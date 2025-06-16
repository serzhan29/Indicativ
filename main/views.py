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
def update_deadline(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item_id = data.get('id')
        item_type = data.get('type')
        month = data.get('month')
        year = data.get('year')

        try:
            if item_type == 'main':
                item = AggregatedIndicator.objects.get(id=item_id)
            else:
                item = TeacherReport.objects.get(id=item_id)

            item.deadline_month = int(month)
            item.deadline_year = int(year)
            item.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class TeacherReportView(LoginRequiredMixin, TemplateView):
    """Генерация отчетов для учителя и их агрегация"""
    template_name = 'main/teacher_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user
        direction_id = self.kwargs['direction_id']
        direction = cache.get_or_set(f'direction_{direction_id}', lambda: get_object_or_404(Direction, id=direction_id),
                                     60 * 60)

        year_id = self.request.GET.get('year_id') or self.kwargs.get('year_id')
        year = cache.get_or_set(f'year_{year_id}', lambda: get_object_or_404(Year, id=year_id),
                                60 * 60) if year_id else Year.objects.last()

        # Список всех лет и направлений (редко обновляется)
        all_years = cache.get_or_set('all_years', lambda: list(Year.objects.all()), 60 * 60)
        all_directions = cache.get_or_set('all_directions', lambda: list(Direction.objects.all()), 60 * 60)

        # Сортировка по коду
        def code_key(code):
            return [int(part) for part in code.split('.') if part.isdigit()]

        # Кэшируем список главных индикаторов
        main_indicators_key = f'main_indicators_dir{direction_id}_year{year.id}'
        main_indicators = cache.get(main_indicators_key)

        if main_indicators is None:
            main_indicators = list(
                MainIndicator.objects.filter(direction=direction, years=year).only('id', 'name', 'code'))
            main_indicators.sort(key=lambda x: code_key(x.code))
            cache.set(main_indicators_key, main_indicators, 60 * 60)

        aggregated_data = []

        for main_indicator in main_indicators:
            # Подиндикаторы — тоже можно кэшировать только имена и id
            indicators_key = f'indicators_main{main_indicator.id}_year{year.id}'
            indicators = cache.get(indicators_key)

            if indicators is None:
                indicators = list(
                    Indicator.objects.filter(main_indicator=main_indicator, years=year).only('id', 'name'))
                cache.set(indicators_key, indicators, 60 * 60)

            # TeacherReport — НЕ кэшируем
            for indicator in indicators:
                teacher_report, created = TeacherReport.objects.get_or_create(
                    teacher=teacher,
                    indicator=indicator,
                    year=year,
                    defaults={'value': 0}
                )
                if not created and teacher_report.value != 0:
                    teacher_report.save()

            # AggregatedIndicator — НЕ кэшируем
            aggregated_indicator, created = AggregatedIndicator.objects.get_or_create(
                main_indicator=main_indicator,
                teacher=teacher,
                year=year,
                defaults={'additional_value': 0}
            )
            if not created and aggregated_indicator.additional_value != 0:
                aggregated_indicator.save()

            total_value = TeacherReport.objects.filter(
                teacher=teacher, indicator__in=indicators, year=year
            ).aggregate(Sum('value'))['value__sum'] or 0

            total_value += aggregated_indicator.additional_value

            teacher_reports = TeacherReport.objects.filter(
                teacher=teacher, indicator__in=indicators, year=year
            ).select_related('indicator')

            for report in teacher_reports:
                report.uploaded_files = report.uploaded_works.all()
                if report.deadline_month and report.deadline_year:
                    report.deadline_display = f"{_(calendar.month_name[report.deadline_month])} {report.deadline_year}"
                else:
                    report.deadline_display = "—"

            if aggregated_indicator.deadline_month and aggregated_indicator.deadline_year:
                aggregated_deadline_display = f"{_(calendar.month_name[aggregated_indicator.deadline_month])} {aggregated_indicator.deadline_year}"
            else:
                aggregated_deadline_display = "—"

            aggregated_data.append({
                'id': aggregated_indicator.id,
                'main_indicator': main_indicator,
                'total_value': total_value,
                'additional_value': aggregated_indicator.additional_value,
                'teacher_reports': teacher_reports,
                'uploaded_works': aggregated_indicator.uploaded_works.all(),
                'deadline_display': aggregated_deadline_display,
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
    """Генерация отчетов для учителя и их агрегация"""
    template_name = 'main/teacher_full_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user

        direction_id = self.kwargs.get('direction_id')
        year_id = self.kwargs.get('year_id')

        directions = Direction.objects.all()
        all_aggregated_data = {}

        if year_id:
            year = get_object_or_404(Year, id=year_id)
        else:
            year = Year.objects.order_by('-id').first()

        if direction_id:
            directions = Direction.objects.filter(id=direction_id)

        for dir_item in directions:
            main_indicators_unsorted = MainIndicator.objects.filter(direction=dir_item, years=year)
            main_indicators = sorted(main_indicators_unsorted, key=lambda x: code_key(x.code))
            aggregated_data = []

            for main_indicator in main_indicators:
                indicators = Indicator.objects.filter(main_indicator=main_indicator, years=year).order_by('code')

                for indicator in indicators:
                    teacher_report, created = TeacherReport.objects.get_or_create(
                        teacher=teacher,
                        indicator=indicator,
                        year=year,
                        defaults={'value': 0}
                    )
                    if not created and teacher_report.value != 0:
                        teacher_report.save()

                aggregated_indicator, created = AggregatedIndicator.objects.get_or_create(
                    main_indicator=main_indicator,
                    teacher=teacher,
                    year=year,
                    defaults={'additional_value': 0}
                )
                if not created and aggregated_indicator.additional_value != 0:
                    aggregated_indicator.save()

                total_value = TeacherReport.objects.filter(
                    teacher=teacher, indicator__in=indicators, year=year
                ).aggregate(Sum('value'))['value__sum'] or 0

                total_value += aggregated_indicator.additional_value

                teacher_reports = TeacherReport.objects.filter(
                    teacher=teacher, indicator__in=indicators, year=year
                ).select_related('indicator')

                for report in teacher_reports:
                    report.uploaded_files = report.uploaded_works.all()
                    if report.deadline_month and report.deadline_year:
                        report.deadline_display = f"{_(calendar.month_name[report.deadline_month])} {report.deadline_year}"
                    else:
                        report.deadline_display = "—"

                # Добавим срок к aggregated_indicator
                if aggregated_indicator.deadline_month and aggregated_indicator.deadline_year:
                    aggregated_deadline_display = f"{_(calendar.month_name[aggregated_indicator.deadline_month])} {aggregated_indicator.deadline_year}"
                else:
                    aggregated_deadline_display = "—"

                aggregated_data.append({
                    'id': aggregated_indicator.id,
                    'main_indicator': main_indicator,
                    'total_value': total_value,
                    'additional_value': aggregated_indicator.additional_value,
                    'teacher_reports': teacher_reports,
                    'uploaded_works': aggregated_indicator.uploaded_works.all(),
                    'deadline_display': aggregated_deadline_display,
                })

            all_aggregated_data[dir_item] = aggregated_data

        context.update({
            'teacher': teacher,
            'current_direction': None if not direction_id else get_object_or_404(Direction, id=direction_id),
            'year': year,
            'all_aggregated_data': all_aggregated_data,
            'directions': Direction.objects.all(),
            'all_years': Year.objects.all().order_by('-year'),
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
    years = Year.objects.order_by('year')
    main_indicators = MainIndicator.objects.all()

    # Получаем все направления
    directions = Direction.objects.all()

    selected_direction = request.GET.get('direction')  # получаем выбранное направление
    selected_indicator = request.GET.get('indicator')  # получаем выбранный главный индикатор

    # Фильтрация по направлению
    if selected_direction:
        main_indicators = main_indicators.filter(direction__id=selected_direction)

    # Фильтрация по главному индикатору
    if selected_indicator:
        main_indicators = main_indicators.filter(id=selected_indicator)

    year_values = []

    for year in years:
        year_data = {
            'year': year.year,
            'main_indicators': []
        }

        for main in main_indicators:
            agg = AggregatedIndicator.objects.filter(
                teacher=teacher,
                main_indicator=main,
                year=year
            ).first()

            year_data['main_indicators'].append({
                'name': main.name,
                'code': main.code,
                'value': agg.total_value if agg else 0,
                'unit': main.unit
            })

        year_values.append(year_data)

    return render(request, 'main/index.html', {
        'teacher': teacher,
        'year_values': year_values,
        'directions': directions,  # передаем список направлений в шаблон
        'selected_direction': selected_direction,  # передаем выбранное направление
        'selected_indicator': selected_indicator,  # передаем выбранный индикатор
        'main_indicators': main_indicators,  # передаем список главных индикаторов для фильтра
    })


