import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Direction, Year, TeacherReport, Indicator, MainIndicator, AggregatedIndicator, User
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

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
    """Генерация отчетов для учителя и их агрегация"""
    teacher = request.user
    direction = get_object_or_404(Direction, id=direction_id)
    year = get_object_or_404(Year, id=year_id)

    # Фильтруем только те главные индикаторы, которые относятся к выбранному году
    main_indicators = MainIndicator.objects.filter(direction=direction, years=year)

    aggregated_data = []
    for main_indicator in main_indicators:
        # Фильтруем только те подиндикаторы, которые относятся к выбранному году
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

        aggregated_data.append({
            'id': aggregated_indicator.id,
            'main_indicator': main_indicator,
            'total_value': total_value,
            'additional_value': aggregated_indicator.additional_value,
            'teacher_reports': teacher_reports
        })

    return render(request, 'main/teacher_report.html', {
        'teacher': teacher,
        'direction': direction,
        'year': year,
        'aggregated_data': aggregated_data
    })



@csrf_exempt
@login_required
def update_value(request):
    """Обновление значений подиндикаторов и доп. значений"""
    if request.method == "POST":
        data = json.loads(request.body)
        item_id = data.get("id")
        new_value = data.get("value")
        item_type = data.get("type")

        try:
            new_value = float(new_value)
        except ValueError:
            return JsonResponse({"success": False, "error": "Некорректное значение"})

        if item_type == "indicator":
            report = TeacherReport.objects.get(id=item_id)
            if not report.year.editable:
                return JsonResponse({"success": False, "error": "Редактирование запрещено"})

            report.value = new_value
            report.save()

            # Пересчет агрегированного значения
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
            aggregated_indicator = AggregatedIndicator.objects.get(id=item_id)
            if not aggregated_indicator.year.editable:
                return JsonResponse({"success": False, "error": "Редактирование запрещено"})

            aggregated_indicator.additional_value = new_value
            aggregated_indicator.total_value = (
                TeacherReport.objects.filter(
                    teacher=aggregated_indicator.teacher, indicator__main_indicator=aggregated_indicator.main_indicator, year=aggregated_indicator.year
                ).aggregate(Sum("value"))["value__sum"] or 0
            ) + new_value  # Прибавляем новое additional_value
            aggregated_indicator.save()

        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "error": "Неверный метод"})


