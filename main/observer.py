from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from user.models import Profile, Faculty, Department
from .models import TeacherReport, AggregatedIndicator, Year, Direction, MainIndicator, Indicator
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from collections import defaultdict
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string


@login_required
def teachers_by_faculty(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return redirect('home')

    if profile.role != 'viewer':
        return render(request, 'main/view/no_permission.html')

    faculties = Faculty.objects.filter(profile__role='teacher').distinct()
    selected_faculty_id = request.GET.get('faculty')
    selected_department_id = request.GET.get('department')

    teachers = Profile.objects.filter(role='teacher')

    if selected_faculty_id:
        teachers = teachers.filter(faculty_id=selected_faculty_id)
        departments = Department.objects.filter(faculty_id=selected_faculty_id)
    else:
        departments = Department.objects.none()

    if selected_department_id:
        teachers = teachers.filter(department_id=selected_department_id)

    teachers = teachers.order_by('user__last_name', 'user__first_name')
    paginator = Paginator(teachers, 18)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'main/view/list_teacher.html', {
        'faculties': faculties,
        'departments': departments,
        'page_obj': page_obj,
        'selected_faculty_id': int(selected_faculty_id) if selected_faculty_id else None,
        'selected_department_id': int(selected_department_id) if selected_department_id else None,
    })



class TeacherReportReadOnlyView(LoginRequiredMixin, TemplateView):
    template_name = 'main/view/teacher_reports_list.html'

    def get(self, request, *args, **kwargs):
        year_id = request.GET.get('year')
        teacher_id = request.GET.get('teacher')

        if not year_id:
            return super().get(request, *args, **kwargs)

        self.year = get_object_or_404(Year, id=year_id)
        self.teacher = get_object_or_404(User, id=teacher_id) if teacher_id else request.user

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        year_id = self.request.GET.get('year')
        directions = Direction.objects.all().order_by('id')
        years = Year.objects.all().order_by('year')

        context['years'] = years
        context['directions'] = directions

        if not year_id:
            return context

        year = self.year
        teacher = self.teacher

        all_data = []

        for direction in directions:
            direction_data = {
                'direction': direction,
                'main_indicators': []
            }

            main_indicators = MainIndicator.objects.filter(direction=direction, years=year)

            for main_indicator in main_indicators:
                indicators = Indicator.objects.filter(main_indicator=main_indicator, years=year)

                total_value = TeacherReport.objects.filter(
                    teacher=teacher, indicator__in=indicators, year=year
                ).aggregate(Sum('value'))['value__sum'] or 0

                aggregated_indicator = AggregatedIndicator.objects.filter(
                    teacher=teacher, main_indicator=main_indicator, year=year
                ).first()

                additional_value = aggregated_indicator.additional_value if aggregated_indicator else 0
                total_value += additional_value

                teacher_reports = TeacherReport.objects.filter(
                    teacher=teacher, indicator__in=indicators, year=year
                ).select_related('indicator')

                direction_data['main_indicators'].append({
                    'main_indicator': main_indicator,
                    'total_value': total_value,
                    'additional_value': additional_value,
                    'teacher_reports': teacher_reports
                })

            all_data.append(direction_data)

        context.update({
            'teacher': teacher,
            'year': year,
            'aggregated_data': all_data  # 👈 Весь список
        })

        return context


def indicator_report_view(request):
    year_id = request.GET.get("year")
    years = Year.objects.all().order_by("-year")
    selected_year = Year.objects.get(id=year_id) if year_id else years.first()

    directions = Direction.objects.all()
    data = []

    for direction in directions:
        direction_data = {
            "name": direction.name,
            "main_indicators": []
        }

        main_indicators = MainIndicator.objects.filter(direction=direction, years=selected_year).prefetch_related("indicators")

        for main in main_indicators:
            has_sub_indicators = main.indicators.exists()
            main_data = {
                "code": main.code,
                "name": main.name,
                "unit": main.unit,
                "teachers": [],
                "total": 0,
                "sub_indicators": [],
                "has_sub_indicators": has_sub_indicators
            }

            if has_sub_indicators:
                for sub in main.indicators.filter(years=selected_year):
                    reports = TeacherReport.objects.filter(indicator=sub, year=selected_year)
                    teacher_values = [(r.teacher.get_full_name() or r.teacher.username, r.value) for r in reports]
                    total = sum(v for _, v in teacher_values)

                    sub_data = {
                        "code": sub.code,
                        "name": sub.name,
                        "unit": sub.unit,
                        "teachers": teacher_values,
                        "total": total
                    }

                    main_data["sub_indicators"].append(sub_data)
            else:
                # Если нет подиндикаторов — смотрим AggregatedIndicator по главному индикатору
                aggr_reports = AggregatedIndicator.objects.filter(main_indicator=main, year=selected_year)
                teacher_values = [(r.teacher.get_full_name() or r.teacher.username, r.total_value) for r in aggr_reports]
                total = sum(v for _, v in teacher_values)

                main_data["teachers"] = teacher_values
                main_data["total"] = total

            direction_data["main_indicators"].append(main_data)

        data.append(direction_data)

        for direction in data:
            for main in direction['main_indicators']:
                if main['has_sub_indicators']:
                    main['sub_total_sum'] = sum(sub['total'] for sub in main['sub_indicators'])


    return render(request, 'main/view/report.html', {
        "years": years,
        "selected_year": selected_year,
        "data": data,
    })


@login_required
def report_department(request):
    year_id = request.GET.get("year")
    department_ids = request.GET.getlist("departments")
    faculty_ids = request.GET.getlist("faculties")  # Новый параметр

    # Получаем список всех лет, и выбираем тот, который был выбран пользователем
    years = Year.objects.all().order_by("-year")
    selected_year = Year.objects.get(id=year_id) if year_id else years.first()

    faculties = Faculty.objects.all()
    departments = Department.objects.all()

    # Если факультеты выбраны, то фильтруем кафедры по ним
    if faculty_ids and 'all' not in faculty_ids:
        selected_faculties = faculties.filter(id__in=faculty_ids)
        selected_departments = departments.filter(faculty__id__in=faculty_ids)
    else:
        selected_faculties = faculties
        selected_departments = departments

    # Применяем фильтрацию для выбранных кафедр
    selected_departments = selected_departments.filter(
        id__in=department_ids) if department_ids else selected_departments

    directions = Direction.objects.all()
    data = []

    # Получаем данные для каждого направления
    for direction in directions:
        direction_data = {
            "name": direction.name,
            "main_indicators": []
        }

        main_indicators = MainIndicator.objects.filter(direction=direction, years=selected_year).prefetch_related(
            "indicators")

        for main in main_indicators:
            has_sub_indicators = main.indicators.exists()
            main_data = {
                "code": main.code,
                "name": main.name,
                "unit": main.unit,
                "teachers": [],
                "total": 0,
                "sub_indicators": [],
                "has_sub_indicators": has_sub_indicators
            }

            if has_sub_indicators:
                for sub in main.indicators.filter(years=selected_year):
                    reports = TeacherReport.objects.filter(indicator=sub, year=selected_year)

                    # Фильтруем отчеты по выбранным кафедрам
                    if selected_departments.exists():
                        reports = reports.filter(teacher__profile__department__in=selected_departments)

                    teacher_values = [(r.teacher.get_full_name() or r.teacher.username, r.value) for r in reports]
                    total = sum(v for _, v in teacher_values)

                    sub_data = {
                        "code": sub.code,
                        "name": sub.name,
                        "unit": sub.unit,
                        "teachers": teacher_values,
                        "total": total
                    }

                    main_data["sub_indicators"].append(sub_data)
            else:
                aggr_reports = AggregatedIndicator.objects.filter(main_indicator=main, year=selected_year)

                # Фильтруем агрегированные отчеты по кафедрам
                if selected_departments.exists():
                    aggr_reports = aggr_reports.filter(teacher__profile__department__in=selected_departments)

                teacher_values = [(r.teacher.get_full_name() or r.teacher.username, r.total_value) for r in
                                  aggr_reports]
                total = sum(v for _, v in teacher_values)

                main_data["teachers"] = teacher_values
                main_data["total"] = total

            direction_data["main_indicators"].append(main_data)

        data.append(direction_data)

    # Считаем сумму по подиндикаторам
    for direction in data:
        for main in direction['main_indicators']:
            if main['has_sub_indicators']:
                main['sub_total_sum'] = sum(sub['total'] for sub in main['sub_indicators'])

    return render(request, 'main/view/report_department.html', {
        "years": years,
        "selected_year": selected_year,
        "data": data,
        "departments": departments,
        "faculties": faculties,
        "selected_departments": [int(d.id) for d in selected_departments],
        "selected_faculties": [int(f.id) for f in selected_faculties],
        "department_map": {
            f.id: list(f.departments.values("id", "name"))
            for f in faculties
        }
    })


# Добавляем представление для получения кафедр в зависимости от факультета
def get_departments(request, faculty_id):
    if faculty_id == 'all':
        departments = Department.objects.all()
    else:
        departments = Department.objects.filter(faculty_id=faculty_id)

    departments_data = [{'id': department.id, 'name': department.name} for department in departments]
    return JsonResponse({'departments': departments_data})

# Графики для проверяющего

@login_required
def observer_index(request):
    user = request.user
    profile = Profile.objects.select_related('faculty', 'department').filter(user=user).first()

    # Получаем фильтры из запроса
    selected_faculty_id = request.GET.get('faculty')
    selected_department_id = request.GET.get('department')
    selected_teacher_id = request.GET.get('teacher')
    selected_direction_id = request.GET.get('direction')
    selected_indicator_id = request.GET.get('indicator')
    selected_year_id = request.GET.get('year')

    # Базовые данные
    faculties = Faculty.objects.all()
    departments = Department.objects.all()
    directions = Direction.objects.all()
    years = Year.objects.order_by('year')
    all_main_indicators = MainIndicator.objects.all()
    profiles = Profile.objects.filter(role='teacher').select_related('user', 'faculty', 'department')

    # Фильтрация данных на основе выбранных фильтров
    if selected_faculty_id:
        faculties = faculties.filter(id=selected_faculty_id)
    if selected_department_id:
        departments = departments.filter(id=selected_department_id)
    if selected_direction_id:
        directions = directions.filter(id=selected_direction_id)
    if selected_indicator_id:
        all_main_indicators = all_main_indicators.filter(id=selected_indicator_id)
    if selected_year_id:
        years = years.filter(id=selected_year_id)

    # Определяем список преподавателей
    if profile and profile.role == 'teacher':
        teachers = [user]
    else:
        if selected_faculty_id:
            profiles = profiles.filter(faculty__id=selected_faculty_id)
        if selected_department_id:
            profiles = profiles.filter(department__id=selected_department_id)
        if selected_teacher_id:
            profiles = profiles.filter(user__id=selected_teacher_id)
        teachers = [p.user for p in profiles]

    # Сбор данных для отображения графиков
    year_values = []

    for year in years:
        year_data = {
            'year': year.year,
            'teachers': []
        }

        for teacher in teachers:
            teacher_data = {
                'teacher': teacher,
                'main_indicators': []
            }

            for main in all_main_indicators:
                agg = AggregatedIndicator.objects.filter(
                    teacher=teacher,
                    main_indicator=main,
                    year=year
                ).first()

                teacher_data['main_indicators'].append({
                    'name': main.name,
                    'code': main.code,
                    'value': agg.total_value if agg else 0,
                    'unit': main.unit
                })

            year_data['teachers'].append(teacher_data)

        year_values.append(year_data)

    # Проверяем, что данные для графиков действительно собраны
    if not year_values:
        print("Нет данных для графика!")

    context = {
        'year_values': year_values,

        # Для фильтров
        'faculties': faculties,
        'departments': departments,
        'teachers': [p.user for p in Profile.objects.filter(role='teacher')],
        'directions': directions,
        'main_indicators': all_main_indicators,
        'years': Year.objects.all(),

        # Выбранные значения
        'selected_faculty_id': selected_faculty_id,
        'selected_department_id': selected_department_id,
        'selected_teacher_id': selected_teacher_id,
        'selected_direction_id': selected_direction_id,
        'selected_indicator_id': selected_indicator_id,
        'selected_year_id': selected_year_id,
    }

    return render(request, 'main/grahics_observer.html', context)
