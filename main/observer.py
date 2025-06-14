import calendar
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
from django.utils.translation import gettext as _
from calendar import month_name


@login_required
def teachers_by_faculty(request):
    user = request.user
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        return redirect('home')

    teachers = Profile.objects.filter(role='teacher')
    selected_faculty_id = request.GET.get('faculty')
    selected_department_id = request.GET.get('department')

    is_superuser = user.is_superuser
    is_dean = profile.role == 'dean'
    is_viewer = profile.role == 'viewer'

    departments = Department.objects.none()
    faculties = Faculty.objects.none()

    # Значения факультета и кафедры для отображения
    selected_faculty = None
    selected_department = None

    if is_superuser:
        faculties = Faculty.objects.all()
        if selected_faculty_id:
            teachers = teachers.filter(faculty_id=selected_faculty_id)
            departments = Department.objects.filter(faculty_id=selected_faculty_id)
            try:
                selected_faculty = Faculty.objects.get(id=selected_faculty_id)
            except Faculty.DoesNotExist:
                selected_faculty = None
        if selected_department_id:
            teachers = teachers.filter(department_id=selected_department_id)
            try:
                selected_department = Department.objects.get(id=selected_department_id)
            except Department.DoesNotExist:
                selected_department = None

    elif is_dean:
        faculties = Faculty.objects.filter(id=profile.faculty_id)
        selected_faculty_id = profile.faculty_id
        teachers = teachers.filter(faculty_id=selected_faculty_id)
        departments = Department.objects.filter(faculty_id=selected_faculty_id)
        try:
            selected_faculty = Faculty.objects.get(id=selected_faculty_id)
        except Faculty.DoesNotExist:
            selected_faculty = None

        if selected_department_id:
            teachers = teachers.filter(department_id=selected_department_id)
            try:
                selected_department = Department.objects.get(id=selected_department_id)
            except Department.DoesNotExist:
                selected_department = None

    elif is_viewer:
        faculties = Faculty.objects.filter(id=profile.faculty_id)
        departments = Department.objects.filter(id=profile.department_id)
        teachers = teachers.filter(
            faculty=profile.faculty,
            department=profile.department
        )
        selected_faculty_id = profile.faculty_id
        selected_department_id = profile.department_id
        selected_faculty = profile.faculty
        selected_department = profile.department

    else:
        return render(request, 'main/view/no_permission.html')

    teachers = teachers.order_by('user__last_name', 'user__first_name')
    paginator = Paginator(teachers, 16)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'main/view/list_teacher.html', {
        'faculties': faculties,
        'departments': departments,
        'page_obj': page_obj,
        'selected_faculty_id': int(selected_faculty_id) if selected_faculty_id else None,
        'selected_department_id': int(selected_department_id) if selected_department_id else None,
        'selected_faculty': selected_faculty,
        'selected_department': selected_department,
        'is_superuser': is_superuser,
        'is_dean': is_dean,
        'is_viewer': is_viewer,
    })


class TeacherReportReadOnlyView(LoginRequiredMixin, TemplateView):
    template_name = 'main/view/teacher_reports_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        year_id = self.request.GET.get('year')
        teacher_id = self.request.GET.get('teacher')

        years = Year.objects.all().order_by('year')
        directions = Direction.objects.all().order_by('id')

        context['years'] = years
        context['directions'] = directions

        # Определение года
        if not year_id and years.exists():
            year = years.last()
        elif year_id:
            year = get_object_or_404(Year, id=year_id)
        else:
            year = None

        # Определение пользователя
        if teacher_id:
            teacher = get_object_or_404(User, id=teacher_id)
        else:
            teacher = self.request.user

        context['year'] = year
        context['teacher'] = teacher

        if not year:
            return context

        all_data = []

        def code_key(code):
            return [int(part) for part in code.split('.') if part.isdigit()]

        for direction in directions:
            direction_data = {
                'direction': direction,
                'main_indicators': []
            }

            main_indicators = list(MainIndicator.objects.filter(direction=direction, years=year))
            main_indicators.sort(key=lambda x: code_key(x.code))

            for main_indicator in main_indicators:
                indicators = Indicator.objects.filter(main_indicator=main_indicator, years=year)

                # Суммарное значение
                total_value = TeacherReport.objects.filter(
                    teacher=teacher, indicator__in=indicators, year=year
                ).aggregate(Sum('value'))['value__sum'] or 0

                # Получение агрегированного индикатора
                aggregated_indicator = AggregatedIndicator.objects.filter(
                    teacher=teacher, main_indicator=main_indicator, year=year
                ).prefetch_related('uploaded_works__co_authors').first()

                additional_value = aggregated_indicator.additional_value if aggregated_indicator else 0
                total_value += additional_value

                # Файлы, загруженные по aggregated_indicator
                uploaded_files = []
                if aggregated_indicator:
                    for f in aggregated_indicator.uploaded_works.all():
                        uploaded_files.append({
                            'file_name': f.file.name.split('/')[-1],
                            'author': teacher.get_full_name() or teacher.username,
                            'co_authors': [u.get_full_name() or u.username for u in f.co_authors.all()],
                            'uploaded_at': f.uploaded_at,
                        })
                    if aggregated_indicator.deadline_month and aggregated_indicator.deadline_year:
                        deadline_display = f"{_(calendar.month_name[aggregated_indicator.deadline_month])} {aggregated_indicator.deadline_year}"
                    else:
                        deadline_display = "—"
                else:
                    deadline_display = "—"

                # Учительские отчёты и их загруженные файлы
                teacher_reports = []
                raw_reports = TeacherReport.objects.filter(
                    teacher=teacher, indicator__in=indicators, year=year
                ).select_related('indicator').prefetch_related('uploaded_works__co_authors')

                for report in raw_reports:
                    report_files = []
                    for f in report.uploaded_works.all():
                        report_files.append({
                            'file_url': f.file.url,
                            'file_name': f.file.name.split('/')[-1],
                            'author': teacher.get_full_name() or teacher.username,
                            'co_authors': [u.get_full_name() or u.username for u in f.co_authors.all()],
                            'uploaded_at': f.uploaded_at,
                        })
                    report.uploaded_file_data = report_files

                    # Срок выполнения
                    if report.deadline_month and report.deadline_year:
                        report.deadline_display = f"{_(calendar.month_name[report.deadline_month])} {report.deadline_year}"
                    else:
                        report.deadline_display = "—"

                    teacher_reports.append(report)

                direction_data['main_indicators'].append({
                    'main_indicator': main_indicator,
                    'total_value': total_value,
                    'additional_value': additional_value,
                    'teacher_reports': teacher_reports,
                    'uploaded_works': uploaded_files,
                    'deadline_display': deadline_display,
                })

            all_data.append(direction_data)

        context['aggregated_data'] = all_data
        return context

@login_required
def report_department(request):
    """кафедра менгерушиси"""
    user_profile = request.user.profile
    user_role = user_profile.role

    year_id = request.GET.get("year")
    department_ids = request.GET.getlist("departments")
    faculty_ids = request.GET.getlist("faculties")

    years = Year.objects.all().order_by("-year")
    selected_year = Year.objects.get(id=year_id) if year_id else years.first()

    all_faculties = Faculty.objects.all()
    all_departments = Department.objects.all()

    # Фильтрация факультетов и кафедр по ролям
    if request.user.is_superuser:
        faculties = all_faculties
        departments = all_departments

    elif user_role == 'viewer':
        faculties = Faculty.objects.filter(id=user_profile.faculty.id) if user_profile.faculty else Faculty.objects.none()
        departments = Department.objects.filter(id=user_profile.department.id) if user_profile.department else Department.objects.none()
        faculty_ids = [str(user_profile.faculty.id)] if user_profile.faculty else []
        department_ids = [str(user_profile.department.id)] if user_profile.department else []

    else:
        faculties = Faculty.objects.none()
        departments = Department.objects.none()

    department_ids = [d for d in department_ids if d != 'all']
    selected_faculties = faculties.filter(id__in=faculty_ids) if faculty_ids else faculties
    selected_departments = departments.filter(id__in=department_ids) if department_ids else departments

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
                "teachers": [],     # для хран. (имя, значение, кол‑во файлов)
                "total": 0,
                "sub_indicators": [],
                "has_sub_indicators": has_sub_indicators
            }

            if has_sub_indicators:
                # Проходим по каждому подиндикатору
                for sub in main.indicators.filter(years=selected_year):
                    reports = TeacherReport.objects.filter(indicator=sub, year=selected_year)
                    if selected_departments.exists():
                        reports = reports.filter(teacher__profile__department__in=selected_departments)

                    teacher_values = []
                    total = 0
                    for r in reports:
                        if r.value > 0:
                            # Считаем количество загруженных файлов для каждого TeacherReport
                            files_count = r.uploaded_works.count()
                            name = r.teacher.get_full_name() or r.teacher.username
                            teacher_values.append((name, r.value, files_count))
                            total += r.value

                    sub_data = {
                        "code": sub.code,
                        "name": sub.name,
                        "unit": sub.unit,
                        "teachers": teacher_values,
                        "total": total
                    }
                    main_data["sub_indicators"].append(sub_data)

            else:
                aggr_qs = AggregatedIndicator.objects.filter(main_indicator=main, year=selected_year)
                if selected_departments.exists():
                    aggr_qs = aggr_qs.filter(teacher__profile__department__in=selected_departments)

                teacher_values = []
                total = 0
                for r in aggr_qs:
                    if r.total_value > 0:
                        # Считаем количество загруженных файлов для AggregatedIndicator
                        files_count = r.uploaded_works.count()
                        name = r.teacher.get_full_name() or r.teacher.username
                        teacher_values.append((name, r.total_value, files_count))
                        total += r.total_value

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
    # 1. Выбор года
    year_id = request.GET.get('year')
    if year_id:
        selected_year = get_object_or_404(Year, id=year_id)
    else:
        selected_year = Year.objects.latest('year')
    years = Year.objects.all().order_by('-year')

    # 2. Профиль, факультет, кафедры, направления
    user_profile = request.user.profile
    faculty = user_profile.faculty
    departments = Department.objects.filter(faculty=faculty)
    directions = Direction.objects.all()

    data = []

    def code_key(code):
        return [int(part) for part in code.split('.') if part.isdigit()]

    # 3. Собираем данные по каждому направлению
    for direction in directions:
        direction_data = {
            'name': direction.name,
            'main_indicators': []
        }

        main_inds = list(MainIndicator.objects.filter(direction=direction, years=selected_year))
        main_inds.sort(key=lambda x: code_key(x.code))

        for main in main_inds:
            indicator_data = {
                'main': main,
                'has_sub': main.indicators.exists(),
                'summary_row': [],
                'sub_indicators': [],
                'row': []
            }

            if main.indicators.exists():
                subs = main.indicators.filter(years=selected_year)
                summary = []

                for dept in departments:
                    total_val = 0
                    teachers_set = set()
                    for sub in subs:
                        qs = TeacherReport.objects.filter(
                            indicator=sub,
                            year=selected_year,
                            teacher__profile__department=dept
                        )
                        total_val += qs.aggregate(total=Sum('value'))['total'] or 0
                        teachers_set |= {r.teacher.get_full_name() for r in qs}
                    summary.append({
                        'value': total_val,
                        'teachers': list(teachers_set)
                    })
                indicator_data['summary_row'] = summary

                # Подиндикаторы
                for sub in subs:
                    sub_row = []
                    for dept in departments:
                        qs = TeacherReport.objects.filter(
                            indicator=sub,
                            year=selected_year,
                            teacher__profile__department=dept
                        )
                        val = qs.aggregate(total=Sum('value'))['total'] or 0

                        teachers = []
                        for r in qs:
                            fc = r.uploaded_works.count()
                            dl = ""
                            if r.deadline_year and r.deadline_month:
                                dl = f"{month_name[r.deadline_month]} {r.deadline_year}"
                            teachers.append({
                                "name":       r.teacher.get_full_name(),
                                "value":      r.value,
                                "file_count": fc,
                                "deadline":   dl,
                            })

                        sub_row.append({
                            'value': val,
                            'teachers': teachers
                        })
                    indicator_data['sub_indicators'].append((sub, sub_row))

            else:
                row = []
                for dept in departments:
                    qs = AggregatedIndicator.objects.filter(
                        main_indicator=main,
                        year=selected_year,
                        teacher__profile__department=dept
                    )
                    val = qs.aggregate(total=Sum('total_value'))['total'] or 0

                    teachers = []
                    for r in qs:
                        fc = r.uploaded_works.count()
                        dl = ""
                        if r.deadline_year and r.deadline_month:
                            dl = f"{month_name[r.deadline_month]} {r.deadline_year}"
                        teachers.append({
                            "name":       r.teacher.get_full_name(),
                            "value":      r.total_value,
                            "file_count": fc,
                            "deadline":   dl,
                        })

                    row.append({
                        'value':    val,
                        'teachers': teachers
                    })
                indicator_data['row'] = row

            direction_data['main_indicators'].append(indicator_data)

        data.append(direction_data)

    return render(request, "main/view/dean_report.html", {
        'faculty':    faculty,
        'departments':departments,
        'data':       data,
        'year':       selected_year,
        'years':      years,
    })

# Добавляем представление для получения кафедр в зависимости от факультета
def get_departments(request, faculty_id):
    if faculty_id == 'all':
        departments = Department.objects.all()
    else:
        departments = Department.objects.filter(faculty_id=faculty_id)

    departments_data = [{'id': department.id, 'name': department.name} for department in departments]
    return JsonResponse({'departments': departments_data})
