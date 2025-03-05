import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Direction, Year, TeacherReport, Indicator, MainIndicator


@login_required
def reports_dashboard(request, direction_id=None, year_id=None):
    """Отображает страницу с выбором направлений, годов и динамической загрузкой отчетов"""
    directions = Direction.objects.all()
    years = Year.objects.all()

    direction = None
    year = None
    reports = []

    if direction_id and year_id:
        direction = get_object_or_404(Direction, id=direction_id)
        year = get_object_or_404(Year, id=year_id)

        main_indicators = MainIndicator.objects.filter(direction=direction, years=year).distinct()
        for main_indicator in main_indicators:
            indicators = Indicator.objects.filter(main_indicator=main_indicator, years=year).distinct()

            report_data = []
            for indicator in indicators:
                report, _ = TeacherReport.objects.get_or_create(
                    teacher=request.user,
                    indicator=indicator,
                    year=year,
                    defaults={'value': 0}
                )
                report_data.append({
                    'id': report.id,
                    'name': indicator.name,
                    'value': report.value
                })

            main_value_total = sum(r['value'] for r in report_data)

            reports.append({
                'main_indicator': main_indicator.name,
                'indicators': report_data,
                'main_value_total': main_value_total
            })

    return render(request, 'main/reports_dashboard.html', {
        'directions': directions,
        'years': years,
        'direction': direction,
        'year': year,
        'reports': reports,
    })


@login_required
@require_POST
def update_report2(request):
    """Обновляет значение индикатора и пересчитывает главный показатель (AJAX)"""
    data = json.loads(request.body)
    report_id = data.get("report_id")
    new_value = data.get("value")

    report = get_object_or_404(TeacherReport, id=report_id, teacher=request.user)

    if not report.year.editable:
        return JsonResponse({"success": False, "error": "Редактирование запрещено для этого года"}, status=403)

    report.value = new_value
    report.save(update_fields=["value"])

    # Пересчитываем общий показатель
    main_indicator = report.indicator.main_indicator
    reports = TeacherReport.objects.filter(
        indicator__main_indicator=main_indicator,
        year=report.year,
        teacher=request.user
    )
    new_main_value = sum(r.value for r in reports)

    # Обновляем `main_value` в каждом отчете
    reports.update(main_value=new_main_value)

    return JsonResponse({
        "success": True,
        "new_main_value": new_main_value
    })

