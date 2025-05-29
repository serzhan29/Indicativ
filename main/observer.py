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
from django.http import JsonResponse


@login_required
def teachers_by_faculty(request):
    if request.user.is_superuser:
        profile = None  # можно вообще не использовать профиль
    else:
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

            def code_key(code):
                return [int(part) for part in code.split('.') if part.isdigit()]

            main_indicators = list(MainIndicator.objects.filter(direction=direction, years=year))
            main_indicators.sort(key=lambda x: code_key(x.code))

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


@login_required
def report_department(request):
    """ кафедра менгерушиси """
    user_profile = request.user.profile  # Получаем профиль пользователя
    user_role = user_profile.role

    year_id = request.GET.get("year")
    department_ids = request.GET.getlist("departments")
    faculty_ids = request.GET.getlist("faculties")

    years = Year.objects.all().order_by("-year")
    selected_year = Year.objects.get(id=year_id) if year_id else years.first()

    all_faculties = Faculty.objects.all()
    all_departments = Department.objects.all()

    # ----------- Фильтрация факультетов и кафедр по ролям ----------- #
    if request.user.is_superuser:
        faculties = all_faculties
        departments = all_departments

    elif user_role == 'viewer':
        # Просмотр кафедры пользователя
        faculties = Faculty.objects.filter(
            id=user_profile.faculty.id) if user_profile.faculty else Faculty.objects.none()
        departments = Department.objects.filter(
            id=user_profile.department.id) if user_profile.department else Department.objects.none()
        faculty_ids = [str(user_profile.faculty.id)] if user_profile.faculty else []
        department_ids = [str(user_profile.department.id)] if user_profile.department else []

    else:  # Для преподавателей и других
        faculties = Faculty.objects.none()
        departments = Department.objects.none()

    # ------------------------------------- #
    # Исключаем 'all' из department_ids
    department_ids = [d for d in department_ids if d != 'all']

    selected_faculties = faculties.filter(id__in=faculty_ids) if faculty_ids else faculties
    selected_departments = departments.filter(id__in=department_ids) if department_ids else departments

    # Получаем направления
    directions = Direction.objects.all()
    data = []

    # Обрабатываем данные для отчета
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

                    if selected_departments.exists():
                        reports = reports.filter(teacher__profile__department__in=selected_departments)

                    teacher_values = [
                        (r.teacher.get_full_name() or r.teacher.username, r.value)
                        for r in reports if r.value > 0
                    ]
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

                if selected_departments.exists():
                    aggr_reports = aggr_reports.filter(teacher__profile__department__in=selected_departments)

                teacher_values = [
                    (r.teacher.get_full_name() or r.teacher.username, r.total_value)
                    for r in aggr_reports if r.total_value > 0
                ]
                total = sum(v for _, v in teacher_values)

                main_data["teachers"] = teacher_values
                main_data["total"] = total

            direction_data["main_indicators"].append(main_data)

        data.append(direction_data)

    # Обработка сумм подиндикаторов
    for direction in data:
        for main in direction['main_indicators']:
            if main['has_sub_indicators']:
                main['sub_total_sum'] = sum(sub['total'] for sub in main['sub_indicators'])

    return render(request, 'main/view/report_department.html', {
        "years": years,
        "selected_year": selected_year,
        "data": data,
        "departments": selected_departments,
        "faculties": selected_faculties,
        "selected_departments": [int(d.id) for d in selected_departments],
        "selected_faculties": [int(f.id) for f in selected_faculties],
        "department_map": {
            f.id: list(f.departments.values("id", "name"))
            for f in selected_faculties
        }
    })


def group_by_department(teacher_values):
    grouped = defaultdict(list)
    totals = {}

    for name, value in teacher_values:
        parts = name.split('—', 1)
        if len(parts) == 2:
            dept_name, teacher_name = parts
        else:
            dept_name = "Неизвестная кафедра"
            teacher_name = name

        grouped[dept_name.strip()].append((teacher_name.strip(), value))
        totals[dept_name.strip()] = totals.get(dept_name.strip(), 0) + value

    return grouped, totals


@login_required
def dean_report(request):
    year_id = request.GET.get('year')
    selected_year = Year.objects.get(id=year_id) if year_id else Year.objects.latest('year')

    # 🔥 Добавим все года для выпадающего списка
    years = Year.objects.all().order_by('-year')

    user_profile = request.user.profile
    faculty = user_profile.faculty
    departments = Department.objects.filter(faculty=faculty)
    directions = Direction.objects.all()

    data = []

    for direction in directions:
        direction_data = {
            'name': direction.name,
            'main_indicators': []
        }

        # Заменяем сортировку на собственную функцию
        def code_key(code):
            return [int(part) for part in code.split('.') if part.isdigit()]

        main_indicators = list(MainIndicator.objects.filter(direction=direction, years=selected_year))
        main_indicators.sort(key=lambda x: code_key(x.code))

        for main in main_indicators:
            indicator_data = {
                'main': main,
                'has_sub': main.indicators.exists(),
                'summary_row': [],
                'sub_indicators': [],
                'row': []
            }

            if main.indicators.exists():
                sub_indicators = main.indicators.filter(years=selected_year)

                dept_sums = []

                for dept in departments:
                    total_value = 0
                    teachers = set()
                    for sub in sub_indicators:
                        reports = TeacherReport.objects.filter(
                            indicator=sub,
                            year=selected_year,
                            teacher__profile__department=dept
                        )
                        value = reports.aggregate(total=Sum('value'))['total'] or 0
                        total_value += value
                        teachers.update([r.teacher.get_full_name() for r in reports])
                    dept_sums.append({'value': total_value, 'teachers': list(teachers)})

                indicator_data['summary_row'] = dept_sums

                for sub in sub_indicators:
                    sub_row = []
                    for dept in departments:
                        reports = TeacherReport.objects.filter(
                            indicator=sub,
                            year=selected_year,
                            teacher__profile__department=dept
                        )
                        value = reports.aggregate(total=Sum('value'))['total'] or 0
                        teachers = [{"name": r.teacher.get_full_name(), "value": r.value} for r in reports]
                        sub_row.append({'value': value, 'teachers': teachers})
                    indicator_data['sub_indicators'].append((sub, sub_row))
            else:
                row = []
                for dept in departments:
                    reports = AggregatedIndicator.objects.filter(
                        main_indicator=main,
                        year=selected_year,
                        teacher__profile__department=dept
                    )
                    value = reports.aggregate(total=Sum('total_value'))['total'] or 0
                    teachers = [{"name": r.teacher.get_full_name(), "value": r.total_value} for r in reports]

                    row.append({'value': value, 'teachers': teachers})
                indicator_data['row'] = row

            direction_data['main_indicators'].append(indicator_data)
        data.append(direction_data)

    return render(request, "main/view/dean_report.html", {
        'faculty': faculty,
        'departments': departments,
        'data': data,
        'year': selected_year,
        'years': years,
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
