import json
import calendar
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import (Direction, Year, TeacherReport, Indicator, MainIndicator, AggregatedIndicator,
                     UploadedWork, UploadedMainWork)
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.views.generic import TemplateView
from django.db.models import Q
from django.utils.translation import gettext as _
from django.core.files.base import ContentFile
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.views.decorators.http import require_POST


@receiver([post_save, post_delete], sender=Direction)
def clear_direction_cache(sender, **kwargs):
    cache.delete("direction_list")


class DirectionListView(LoginRequiredMixin, ListView):
    """Шаг 1: Выбор направления (с кэшированием queryset)"""
    model = Direction
    template_name = 'main/direction_list.html'
    context_object_name = 'directions'

    def get_queryset(self):
        cache_key = "direction_list"
        queryset = cache.get(cache_key)
        if queryset is None:
            queryset = Direction.objects.all()
            cache.set(cache_key, queryset, 300)
        return queryset


class YearListView(LoginRequiredMixin, ListView):
    """Шаг 2: Выбор года после направления"""
    model = Year
    template_name = 'main/year_list.html'
    context_object_name = 'years'

    def get_queryset(self):
        return Year.objects.filter(
            mainindicator__direction__id=self.kwargs['direction_id']
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['direction'] = get_object_or_404(Direction, id=self.kwargs['direction_id'])
        return context


class FileModalView(LoginRequiredMixin, View):
    """
    GET  — возвращает JSON со списком учителей (co-authors) и уже загруженных файлов.
    POST — сохраняет новую загрузку (с co_authors).
    """

    def get(self, request, report_id):
        user = request.user
        rpt_type = request.GET.get('type')  # 'sub' или 'main'

        # --- 1) Список co‑authors: все учителя из той же кафедры ---
        dept = getattr(user.profile, 'department', None)
        if dept:
            teachers = User.objects.filter(
                profile__department=dept,
                profile__role='teacher'
            ).order_by('last_name', 'first_name')
        else:
            teachers = User.objects.none()

        teachers_list = [
            {'id': t.id, 'name': t.get_full_name() or t.username}
            for t in teachers if t != user
        ]

        # --- 2) Список уже загруженных файлов ---
        if rpt_type == 'sub':
            qs = UploadedWork.objects.filter(
                Q(report__id=report_id) &
                (Q(report__teacher=user) | Q(co_authors=user))
            )
        else:  # main
            qs = UploadedMainWork.objects.filter(
                Q(aggregated_report__id=report_id) &
                (Q(aggregated_report__teacher=user) | Q(co_authors=user))
            )

        files_data = []
        for f in qs.distinct():
            # определяем владельца и список соавторов
            owner = f.report.teacher if rpt_type == 'sub' else f.aggregated_report.teacher
            co_list = list(f.co_authors.all())
            if owner not in co_list:
                co_list.insert(0, owner)

            files_data.append({
                'id': f.id,
                'name': f.file.name.rsplit('/', 1)[-1],
                'uploaded_at': f.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                'url': f.file.url,
                'co_authors': [u.get_full_name() or u.username for u in co_list],
                'is_owner': owner == user
            })

        return JsonResponse({
            'teachers': teachers_list,
            'files': files_data
        })


    def post(self, request, report_id):
        user = request.user
        rpt_type = request.POST.get('report_type')

        if 'file' not in request.FILES:
            return HttpResponseBadRequest("No file attached")

        uploaded_file = request.FILES['file']
        co_ids = request.POST.getlist('co_authors')

        # Всегда включаем текущего пользователя
        if str(user.id) not in co_ids:
            co_ids.append(str(user.id))

        # Считываем файл в память один раз
        original_file_content = uploaded_file.read()
        original_file_name = uploaded_file.name

        if rpt_type == 'sub':
            base_report = get_object_or_404(TeacherReport, id=report_id)
            indicator = base_report.indicator  # ← исправлено
            year = base_report.year

            for co_id in co_ids:
                co_user = get_object_or_404(User, id=co_id)

                teacher_report, _ = TeacherReport.objects.get_or_create(
                    teacher=co_user,
                    indicator=indicator,  # ← исправлено
                    year=year,
                    defaults={'value': 0, 'additional_value': 0}
                )

                file_copy = ContentFile(original_file_content)
                file_copy.name = original_file_name

                uploaded = UploadedWork.objects.create(
                    report=teacher_report,
                    file=file_copy
                )
                uploaded.co_authors.set(co_ids)


        elif rpt_type == 'main':
            base_report = get_object_or_404(AggregatedIndicator, id=report_id)
            main_indicator = base_report.main_indicator
            year = base_report.year

            for co_id in co_ids:
                co_user = get_object_or_404(User, id=co_id)

                agg_report, _ = AggregatedIndicator.objects.get_or_create(
                    teacher=co_user,
                    main_indicator=main_indicator,
                    year=year,
                    defaults={'total_value': 0, 'additional_value': 0}
                )

                file_copy = ContentFile(original_file_content)
                file_copy.name = original_file_name

                uploaded = UploadedMainWork.objects.create(
                    aggregated_report=agg_report,
                    file=file_copy
                )
                uploaded.co_authors.set(co_ids)

        else:
            return HttpResponseBadRequest("Bad report_type")

        return JsonResponse({'success': True, 'message': 'Файл успешно загружен для всех соавторов.'})


class FileDeleteView(LoginRequiredMixin, View):
    """
    POST — удаляет файл, если текущий user — владелец или co_author.
    """
    def post(self, request, file_id):
        user = request.user
        from django.db.models import Q

        obj = (UploadedWork.objects.filter(
                    Q(id=file_id) & (Q(report__teacher=user) | Q(co_authors=user))
               ).first()
               or UploadedMainWork.objects.filter(
                    Q(id=file_id) & (Q(aggregated_report__teacher=user) | Q(co_authors=user))
               ).first())

        if not obj:
            return HttpResponseForbidden("Нет доступа")
        obj.file.delete(save=False)
        obj.delete()
        return JsonResponse({'success': True})


@csrf_exempt
@require_POST
def update_deadline(request):
    # 1) Проверка типа содержимого и JSON
    if request.content_type != 'application/json':
        return HttpResponseBadRequest('Content-Type must be application/json')

    try:
        data = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HttpResponseBadRequest('Invalid JSON')

    # 2) Достаём и валидируем поля
    item_id = data.get('id')
    item_type = data.get('type')
    month = data.get('month')
    year = data.get('year')

    if item_id is None or item_type is None or month is None or year is None:
        return HttpResponseBadRequest('Missing required fields: id, type, month, year')

    try:
        item_id = int(item_id)
        month = int(month)
        year = int(year)
    except (TypeError, ValueError):
        return HttpResponseBadRequest('id, month, year must be integers')

    if not 1 <= month <= 12:
        return HttpResponseBadRequest('month must be between 1 and 12')

    # 3) Определяем модель по типу
    if item_type == 'main':
        Model = AggregatedIndicator
    elif item_type == 'teacher':
        Model = TeacherReport
    else:
        return HttpResponseBadRequest('Invalid type: expected "main" or "teacher"')

    # 4) Ищем запись и сохраняем изменения
    try:
        item = Model.objects.get(id=item_id)
    except Model.DoesNotExist:
        return HttpResponseBadRequest('Item not found')

    item.deadline_month = month
    item.deadline_year = year
    item.save(update_fields=['deadline_month', 'deadline_year'])

    return JsonResponse({'success': True})


class TeacherReportView(LoginRequiredMixin, TemplateView):
    """Генерация отчетов для учителя и их агрегация"""
    template_name = 'main/teacher_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user
        direction_id = self.kwargs['direction_id']
        direction = cache.get_or_set(
            f'direction_{direction_id}',
            lambda: get_object_or_404(Direction, id=direction_id),
            60 * 60
        )

        year_id = self.request.GET.get('year_id') or self.kwargs.get('year_id')
        year = cache.get_or_set(
            f'year_{year_id}',
            lambda: get_object_or_404(Year, id=year_id),
            60 * 60
        ) if year_id else Year.objects.last()

        all_years = cache.get_or_set('all_years', lambda: list(Year.objects.all()), 60 * 60)
        all_directions = cache.get_or_set('all_directions', lambda: list(Direction.objects.all()), 60 * 60)

        # Загрузка основных индикаторов с кешированием
        def code_key(code):
            return [int(part) for part in code.split('.') if part.isdigit()]

        main_key = f'main_indicators_dir{direction_id}_year{year.id}'
        main_indicators = cache.get(main_key)
        if main_indicators is None:
            main_indicators = list(
                MainIndicator.objects.filter(direction=direction, years=year)
                .only('id', 'name', 'code')
            )
            main_indicators.sort(key=lambda x: code_key(x.code))
            cache.set(main_key, main_indicators, 60 * 60)

        # Загрузка всех подиндикаторов сразу и группировка по main_indicator_id
        indicators_qs = Indicator.objects.filter(
            main_indicator__in=main_indicators,
            years=year
        ).only('id', 'name', 'main_indicator_id')
        indicators_by_main = {}
        for ind in indicators_qs:
            indicators_by_main.setdefault(ind.main_indicator_id, []).append(ind)

        # Загрузка существующих отчетов учителя
        all_indicators = [ind for sub in indicators_by_main.values() for ind in sub]
        tr_qs = TeacherReport.objects.filter(
            teacher=teacher,
            indicator__in=all_indicators,
            year=year
        ).select_related('indicator').prefetch_related('uploaded_works')
        tr_dict = {tr.indicator_id: tr for tr in tr_qs}

        # Загрузка аггрегированных индикаторов
        ai_qs = AggregatedIndicator.objects.filter(
            teacher=teacher,
            main_indicator__in=main_indicators,
            year=year
        ).prefetch_related('uploaded_works')
        ai_dict = {ai.main_indicator_id: ai for ai in ai_qs}

        aggregated_data = []
        for main in main_indicators:
            sub_inds = indicators_by_main.get(main.id, [])

            # Обработка TeacherReport
            current_trs = []
            for ind in sub_inds:
                tr = tr_dict.get(ind.id)
                if tr:
                    if tr.value != 0:
                        tr.save()
                else:
                    tr = TeacherReport.objects.create(
                        teacher=teacher,
                        indicator=ind,
                        year=year,
                        value=0
                    )
                    tr.uploaded_works.set([])
                # Формат отображения дедлайна для tr
                if tr.deadline_month and tr.deadline_year:
                    tr.deadline_display = f"{_(calendar.month_name[tr.deadline_month])} {tr.deadline_year}"
                else:
                    tr.deadline_display = "—"
                current_trs.append(tr)

            # Обработка AggregatedIndicator
            ai = ai_dict.get(main.id)
            if ai:
                if ai.additional_value != 0:
                    ai.save()
            else:
                ai = AggregatedIndicator.objects.create(
                    main_indicator=main,
                    teacher=teacher,
                    year=year,
                    additional_value=0
                )
                ai.uploaded_works.set([])

            if ai.deadline_month and ai.deadline_year:
                ai_deadline = f"{_(calendar.month_name[ai.deadline_month])} {ai.deadline_year}"
            else:
                ai_deadline = "—"

            # Подсчет суммарного значения
            total = sum(tr.value for tr in current_trs) + ai.additional_value

            aggregated_data.append({
                'id': ai.id,
                'main_indicator': main,
                'total_value': total,
                'additional_value': ai.additional_value,
                'teacher_reports': current_trs,
                'uploaded_works': ai.uploaded_works.all(),
                'deadline_display': ai_deadline,
            })

        months = [(i, _(calendar.month_name[i])) for i in range(1, 13)]

        context.update({
            'teacher': teacher,
            'direction': direction,
            'year': year,
            'all_years': all_years,
            'aggregated_data': aggregated_data,
            'directions': all_directions,
            'months': months,
        })
        return context

def code_key(code):
    return [int(part) for part in code.split('.') if part.isdigit()]


class TeacherReportAllDirection(LoginRequiredMixin, TemplateView):
    """Генерация отчетов для учителя по всем направлениям и их агрегация"""
    template_name = 'main/teacher_full_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user

        direction_id = self.kwargs.get('direction_id')
        year_id = self.kwargs.get('year_id')

        # Определяем год
        if year_id:
            year = get_object_or_404(Year, id=year_id)
        else:
            year = cache.get_or_set('latest_year', lambda: Year.objects.order_by('-id').first(), 60 * 60)

        # Определяем список направлений
        if direction_id:
            directions = Direction.objects.filter(id=direction_id)
        else:
            directions = cache.get_or_set('all_directions_list', lambda: list(Direction.objects.all()), 60 * 60)

        # Загрузка главных индикаторов для всех направлений
        mi_qs = MainIndicator.objects.filter(direction__in=directions, years=year).only('id', 'name', 'code', 'direction_id')
        mi_by_dir = {}
        all_main_ids = []
        for mi in mi_qs:
            mi_by_dir.setdefault(mi.direction_id, []).append(mi)
            all_main_ids.append(mi.id)

        # Сортировка списков главных индикаторов по коду
        for dir_id, mis in mi_by_dir.items():
            mi_by_dir[dir_id] = sorted(mis, key=lambda x: code_key(x.code))

        # Загрузка подиндикаторов для всех главных
        ind_qs = Indicator.objects.filter(main_indicator_id__in=all_main_ids, years=year).only('id', 'name', 'main_indicator_id', 'code')
        inds_by_main = {}
        for ind in ind_qs:
            inds_by_main.setdefault(ind.main_indicator_id, []).append(ind)
        # Сортируем по коду
        for mi_id, inds in inds_by_main.items():
            inds_by_main[mi_id] = sorted(inds, key=lambda x: code_key(x.code))

        # Подготовка всех необходимых TeacherReport и AggregatedIndicator
        all_inds = [ind for sub in inds_by_main.values() for ind in sub]
        tr_qs = TeacherReport.objects.filter(teacher=teacher, indicator__in=all_inds, year=year)
        tr_qs = tr_qs.select_related('indicator').prefetch_related('uploaded_works')
        tr_dict = {tr.indicator_id: tr for tr in tr_qs}

        ai_qs = AggregatedIndicator.objects.filter(teacher=teacher, main_indicator_id__in=all_main_ids, year=year)
        ai_qs = ai_qs.prefetch_related('uploaded_works')
        ai_dict = {ai.main_indicator_id: ai for ai in ai_qs}

        # Сбор данных
        all_aggregated_data = {}
        for dir_obj in directions:
            dir_data = []
            mains = mi_by_dir.get(dir_obj.id, [])
            for main in mains:
                # Формируем отчеты для подиндикаторов
                reports = []
                sub_inds = inds_by_main.get(main.id, [])
                for ind in sub_inds:
                    tr = tr_dict.get(ind.id)
                    if tr:
                        if tr.value != 0:
                            tr.save()
                    else:
                        tr = TeacherReport.objects.create(
                            teacher=teacher,
                            indicator=ind,
                            year=year,
                            value=0
                        )
                        tr.uploaded_works.set([])
                    # Формат дедлайна
                    if tr.deadline_month and tr.deadline_year:
                        tr.deadline_display = f"{_(calendar.month_name[tr.deadline_month])} {tr.deadline_year}"
                    else:
                        tr.deadline_display = "—"
                    reports.append(tr)

                # Обработка агрегированного индикатора
                ai = ai_dict.get(main.id)
                if ai:
                    if ai.additional_value != 0:
                        ai.save()
                else:
                    ai = AggregatedIndicator.objects.create(
                        main_indicator=main,
                        teacher=teacher,
                        year=year,
                        additional_value=0
                    )
                    ai.uploaded_works.set([])
                if ai.deadline_month and ai.deadline_year:
                    ai_deadline = f"{_(calendar.month_name[ai.deadline_month])} {ai.deadline_year}"
                else:
                    ai_deadline = "—"

                # Подсчет суммарного значения
                total_val = sum(r.value for r in reports) + ai.additional_value

                dir_data.append({
                    'id': ai.id,
                    'main_indicator': main,
                    'total_value': total_val,
                    'additional_value': ai.additional_value,
                    'teacher_reports': reports,
                    'uploaded_works': ai.uploaded_works.all(),
                    'deadline_display': ai_deadline,
                })

            all_aggregated_data[dir_obj] = dir_data

        context.update({
            'teacher': teacher,
            'current_direction': None if not direction_id else get_object_or_404(Direction, id=direction_id),
            'year': year,
            'all_aggregated_data': all_aggregated_data,
            'directions': directions,
            'all_years': cache.get_or_set('years_list', lambda: list(Year.objects.all().order_by('-year')), 60 * 60),
            'months': [(i, _(calendar.month_name[i])) for i in range(1, 13)],
        })
        return context



@method_decorator(csrf_exempt, name='dispatch')
class UpdateValueView(LoginRequiredMixin, View):
    """Обновление значений подиндикаторов и доп. значений"""

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        item_id = data.get("id")
        new_value = data.get("value")
        item_type = data.get("type")

        try:
            new_value = float(new_value)
        except ValueError:
            return JsonResponse({"success": False, "error": "Некорректное значение"})

        if item_type == "indicator":
            report = get_object_or_404(TeacherReport, id=item_id)
            if not report.year.editable:
                return JsonResponse({"success": False, "error": "Редактирование запрещено"})

            report.value = new_value
            report.save()

            aggregated_indicator, _ = AggregatedIndicator.objects.get_or_create(
                main_indicator=report.indicator.main_indicator,
                teacher=report.teacher,
                year=report.year,
            )
            aggregated_indicator.total_value = (
                TeacherReport.objects.filter(
                    teacher=report.teacher, indicator__main_indicator=report.indicator.main_indicator, year=report.year
                ).aggregate(Sum("value"))["value__sum"] or 0
            ) + aggregated_indicator.additional_value
            aggregated_indicator.save()

        elif item_type == "additional":
            aggregated_indicator = get_object_or_404(AggregatedIndicator, id=item_id)
            if not aggregated_indicator.year.editable:
                return JsonResponse({"success": False, "error": "Редактирование запрещено"})

            aggregated_indicator.additional_value = new_value
            aggregated_indicator.total_value = (
                TeacherReport.objects.filter(
                    teacher=aggregated_indicator.teacher, indicator__main_indicator=aggregated_indicator.main_indicator, year=aggregated_indicator.year
                ).aggregate(Sum("value"))["value__sum"] or 0
            ) + new_value
            aggregated_indicator.save()

        return JsonResponse({"success": True})

    def get(self, request, *args, **kwargs):
        return JsonResponse({"success": False, "error": "Неверный метод"})


# index.html
@login_required
def index(request):
    teacher = request.user

    # Кэшируем список годов и направлений (редко меняются)
    years = cache.get_or_set('years_list', lambda: list(Year.objects.order_by('year')), 60 * 60)
    directions = cache.get_or_set('directions_list', lambda: list(Direction.objects.all()), 60 * 60)

    # Получаем и фильтруем главные индикаторы
    main_qs = MainIndicator.objects.all().only('id', 'name', 'code', 'unit', 'direction_id')
    selected_direction = request.GET.get('direction')
    selected_indicator = request.GET.get('indicator')

    if selected_direction:
        main_qs = main_qs.filter(direction_id=selected_direction)
    if selected_indicator:
        main_qs = main_qs.filter(id=selected_indicator)

    main_indicators = list(main_qs)

    # Подгружаем все AggregatedIndicator одной операцией
    agg_qs = AggregatedIndicator.objects.filter(
        teacher=teacher,
        main_indicator__in=main_indicators,
        year__in=years
    ).select_related('year', 'main_indicator')

    # Создаем словарь (year_id, main_id) -> AggregatedIndicator
    agg_dict = {(ai.year_id, ai.main_indicator_id): ai for ai in agg_qs}

    year_values = []

    for year in years:
        row = {'year': year.year, 'main_indicators': []}
        for main in main_indicators:
            ai = agg_dict.get((year.id, main.id))
            value = ai.additional_value if ai else 0
            row['main_indicators'].append({
                'name': main.name,
                'code': main.code,
                'value': value,
                'unit': main.unit
            })
        year_values.append(row)

    return render(request, 'main/index.html', {
        'teacher': teacher,
        'year_values': year_values,
        'directions': directions,
        'selected_direction': selected_direction,
        'selected_indicator': selected_indicator,
        'main_indicators': main_indicators,
    })



