from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import TeacherReport, SubIndicator, Direction, Year, MainIndicator
from django.db import transaction


@login_required
def direction_list(request):
    directions = Direction.objects.all()
    return render(request, 'main/direction_list.html', {'directions': directions})

@login_required
def year_list(request, direction_id):
    direction = get_object_or_404(Direction, id=direction_id)
    # Выбираем годы, для которых существуют главные индикаторы с выбранным направлением
    main_indicators = MainIndicator.objects.filter(direction=direction)
    years = Year.objects.filter(mainindicator__in=main_indicators).distinct().order_by('year')
    return render(request, 'main/year_list.html', {'direction': direction, 'years': years})


@login_required
def report_list(request, direction_id, year):
    direction = get_object_or_404(Direction, id=direction_id)
    year_obj = get_object_or_404(Year, year=year)
    teacher = request.user

    # Находим все главные индикаторы для выбранного направления и года
    main_indicators = MainIndicator.objects.filter(direction=direction, years=year_obj)

    reports = []
    for main in main_indicators:
        sub_indicators = SubIndicator.objects.filter(main_indicator=main, year=year_obj)
        for sub in sub_indicators:
            report, created = TeacherReport.objects.get_or_create(
                teacher=teacher,
                sub_indicator=sub,
                defaults={'custom_value': sub.default_value}
            )
            reports.append(report)

    context = {
        'direction': direction,
        'year': year_obj,
        'reports': reports,
    }
    return render(request, 'main/report_list.html', context)


@login_required
def report_detail(request, report_id):
    # Получаем конкретный отчет для текущего учителя
    report = get_object_or_404(TeacherReport, id=report_id, teacher=request.user)

    if request.method == 'POST':
        # Например, редактирование custom_value
        new_value = request.POST.get('custom_value')
        try:
            report.custom_value = int(new_value)
            report.save()
            return redirect('report_detail', report_id=report.id)
        except (ValueError, TypeError):
            error = "Введите корректное числовое значение"
            return render(request, 'main/report_detail.html', {'report': report, 'error': error})

    return render(request, 'main/report_detail.html', {'report': report})
