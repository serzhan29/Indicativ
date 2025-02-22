import json

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .models import Direction, Year, TeacherReport, Indicator, MainIndicator
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse

@login_required
def choose_direction(request):
    """Шаг 1: Выбор направления"""
    directions = Direction.objects.all()
    return render(request, 'main/direction_list.html', {'directions': directions})

@login_required
def choose_year(request, direction_id):
    """Шаг 2: Выбор года после направления"""
    direction = get_object_or_404(Direction, id=direction_id)
    years = Year.objects.all()
    return render(request, 'main/year_list.html', {'direction': direction, 'years': years})


@login_required
def teacher_report(request, direction_id, year_id):
    """Отображает отчет учителя по выбранному направлению и году"""
    direction = get_object_or_404(Direction, id=direction_id)
    year = get_object_or_404(Year, id=year_id)
    main_indicators = MainIndicator.objects.filter(direction=direction, years=year)

    reports = []
    for main_indicator in main_indicators:
        indicators = Indicator.objects.filter(main_indicator=main_indicator, years=year)
        report_data = []

        for indicator in indicators:
            report, created = TeacherReport.objects.get_or_create(
                teacher=request.user,
                indicator=indicator,
                year=year,  # Указываем год, чтобы значения были уникальными для каждого года
                defaults={'value': 0}
            )
            report_data.append(report)

        # Автоматический пересчет главного индикатора
        main_value_total = sum(r.value for r in report_data)

        # Обновляем значение в базе данных
        for report in report_data:
            report.main_value = main_value_total
            report.save(update_fields=["main_value"])

        reports.append({
            'main_indicator': main_indicator,
            'indicators': report_data,
            'main_value_total': main_value_total
        })

    return render(request, 'main/report_detail.html', {
        'direction': direction,
        'year': year,
        'reports': reports
    })



@login_required
@require_POST
def update_report(request):
    """Обновляет значение индикатора и пересчитывает главный показатель"""
    data = json.loads(request.body)
    report_id = data.get("report_id")
    new_value = data.get("value")

    report = get_object_or_404(TeacherReport, id=report_id, teacher=request.user)
    report.value = new_value
    report.save(update_fields=["value"])

    # Пересчет главного значения
    main_indicator = report.indicator.main_indicator
    reports = TeacherReport.objects.filter(
        indicator__main_indicator=main_indicator,
        year=report.year,
        teacher=request.user
    )
    new_main_value = sum(r.value for r in reports)

    # Обновляем у всех связанных записей
    reports.update(main_value=new_main_value)

    return JsonResponse({"success": True, "new_main_value": new_main_value})
