import json
import calendar
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import (Direction, Year, TeacherReport, Indicator, MainIndicator, AggregatedIndicator,
                     UploadedWork, UploadedMainWork)
from user.models import Department, Faculty, Profile
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.views.generic import TemplateView
from django.db.models import Q
from django.utils.translation import gettext as _


class DirectionListView(LoginRequiredMixin, ListView):
    """Шаг 1: Выбор направления"""
    model = Direction
    template_name = 'main/direction_list.html'
    context_object_name = 'directions'


class YearListView(LoginRequiredMixin, ListView):
    """Шаг 2: Выбор года после направления"""
    model = Year
    template_name = 'main/year_list.html'
    context_object_name = 'years'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['direction'] = get_object_or_404(Direction, id=self.kwargs['direction_id'])
        return context


@login_required
def get_all_users(request):
    try:
        current_profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'users': []})  # если профиль не найден

    if not current_profile.department:
        return JsonResponse({'users': []})  # если не указана кафедра

    # Получаем всех пользователей, кроме себя, с той же кафедры и ролью "teacher"
    same_department_profiles = Profile.objects.filter(
        department=current_profile.department,
        role='teacher'
    ).exclude(user=request.user)

    users_data = [
        {'id': p.user.id, 'name': p.user.get_full_name()}
        for p in same_department_profiles
    ]

    return JsonResponse({'users': users_data})


@login_required
def get_indicator_files(request, report_id):
    """
    Загрузка и отображение файлов по подиндикаторам и главным индикаторам
    Делаем фильтр строго по report_id, но берём все записи, где пользователь —
    либо автор отчёта, либо входит в co_authors.
    """

    user = request.user

    # POST: сохраняем файл
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        co_author_ids = request.POST.getlist('co_authors')

        # Всегда включаем автора
        author_id = str(user.id)
        if author_id not in co_author_ids:
            co_author_ids.append(author_id)

        if 'indicator' in request.POST:
            report = get_object_or_404(TeacherReport, id=report_id, teacher=user)
            new_file = report.uploaded_works.create(file=uploaded_file)
        else:
            report = get_object_or_404(AggregatedIndicator, id=report_id, teacher=user)
            new_file = report.uploaded_works.create(file=uploaded_file)

        new_file.co_authors.set(co_author_ids)
        return JsonResponse({'success': True, 'message': 'Файл успешно загружен.'})

    files_data = []

    # 1) Подиндикаторы — строго для этого report_id
    sub_qs = UploadedWork.objects.filter(
        Q(report__id=report_id) &
        (Q(report__teacher=user) | Q(co_authors=user))
    ).distinct()

    for f in sub_qs:
        # Список соавторов + автор
        co_list = list(f.co_authors.all())
        if f.report.teacher not in co_list:
            co_list.insert(0, f.report.teacher)

        files_data.append({
            'id': f.id,
            'file_name': f.file.name.split('/')[-1],
            'uploaded_at': f.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
            'file_url': f.file.url,
            'co_authors': [u.get_full_name() for u in co_list],
            'owner': f.report.teacher.get_full_name(),
            'is_owner': f.report.teacher == user
        })

    # 2) Главные индикаторы — строго для этого aggregated_report__id
    main_qs = UploadedMainWork.objects.filter(
        Q(aggregated_report__id=report_id) &
        (Q(aggregated_report__teacher=user) | Q(co_authors=user))
    ).distinct()

    for f in main_qs:
        co_list = list(f.co_authors.all())
        if f.aggregated_report.teacher not in co_list:
            co_list.insert(0, f.aggregated_report.teacher)

        files_data.append({
            'id': f.id,
            'file_name': f.file.name.split('/')[-1],
            'uploaded_at': f.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
            'file_url': f.file.url,
            'co_authors': [u.get_full_name() for u in co_list],
            'owner': f.aggregated_report.teacher.get_full_name(),
            'is_owner': f.aggregated_report.teacher == user
        })

    return JsonResponse({'files': files_data})



@require_POST
def delete_uploaded_file(request, file_id):
    # сначала пытаемся в UploadedWork
    obj = UploadedWork.objects.filter(id=file_id, report__teacher=request.user).first()
    if not obj:
        # иначе в UploadedMainWork
        obj = UploadedMainWork.objects.filter(id=file_id, aggregated_report__teacher=request.user).first()
    if not obj:
        return JsonResponse({'success': False, 'message': 'Файл не найден.'}, status=404)

    # удаляем сам файл и запись
    obj.file.delete(save=False)
    obj.delete()
    return JsonResponse({'success': True, 'message': 'Файл удалён.'})


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
        direction = get_object_or_404(Direction, id=self.kwargs['direction_id'])

        # Получаем год либо из URL (kwargs), либо из GET-параметра
        year_id = self.request.GET.get('year_id') or self.kwargs.get('year_id')
        year = get_object_or_404(Year, id=year_id) if year_id else Year.objects.last()

        # Заменяем сортировку на собственную функцию
        def code_key(code):
            return [int(part) for part in code.split('.') if part.isdigit()]

        main_indicators = list(MainIndicator.objects.filter(direction=direction, years=year))
        main_indicators.sort(key=lambda x: code_key(x.code))
        aggregated_data = []

        for main_indicator in main_indicators:
            indicators = Indicator.objects.filter(main_indicator=main_indicator, years=year)

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

        # Список месяцев через calendar с локализацией
        months = [(i, _(calendar.month_name[i])) for i in range(1, 13)]

        context.update({
            'teacher': teacher,
            'direction': direction,
            'year': year,
            'all_years': Year.objects.all(),
            'aggregated_data': aggregated_data,
            'directions': Direction.objects.all(),
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


