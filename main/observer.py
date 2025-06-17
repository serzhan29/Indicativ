import calendar
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from user.models import Profile, Faculty, Department
from .models import TeacherReport, AggregatedIndicator, Year, Direction, MainIndicator, Indicator
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from django.core.cache import cache
from django.views import View
from django.utils.decorators import method_decorator


class TeachersByFacultyView(LoginRequiredMixin, TemplateView):
    """
    Показывает список всех преподавателей.
    Если входит администратор, он может выбирать любые факультеты и кафедры.
    Если входит заместитель заведующего кафедрой, он/она не может выбирать — отображаются только его/её факультет и кафедра.
    Если входит декан, он/она может выбирать кафедры, но не может выбрать факультет.
    """
    template_name = 'main/view/list_teacher.html'

    def get_context_data(self, **kwargs):
        request = self.request
        user = request.user

        # Попытка получить профиль пользователя
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return redirect('home')

        # Роли пользователя
        is_superuser = user.is_superuser
        is_dean = profile.role == 'dean'
        is_viewer = profile.role == 'viewer'

        # Если у пользователя нет нужной роли — нет доступа
        if not (is_superuser or is_dean or is_viewer):
            return super().render_to_response({'no_permission': True})

        # Кэширование справочников факультетов и кафедр
        faculties = cache.get_or_set(
            'faculties_list',
            lambda: list(Faculty.objects.all().only('id', 'name')),
            60 * 60
        )
        all_departments = cache.get_or_set(
            'departments_list',
            lambda: list(Department.objects.all().only('id', 'name', 'faculty_id')),
            60 * 60
        )

        # Базовый queryset преподавателей
        teachers_qs = Profile.objects.filter(role='teacher').select_related('user', 'faculty', 'department')

        # Параметры фильтрации из запроса
        selected_faculty_id = request.GET.get('faculty')
        selected_department_id = request.GET.get('department')

        # Факультеты и кафедры доступные пользователю в зависимости от роли
        if is_superuser:
            visible_faculties = faculties
            visible_departments = all_departments
        elif is_dean:
            visible_faculties = [f for f in faculties if f.id == profile.faculty_id]
            visible_departments = [d for d in all_departments if d.faculty_id == profile.faculty_id]
            selected_faculty_id = selected_faculty_id or profile.faculty_id
        else:  # is_viewer
            visible_faculties = [f for f in faculties if f.id == profile.faculty_id]
            visible_departments = [d for d in all_departments if d.id == profile.department_id]
            selected_faculty_id = profile.faculty_id
            selected_department_id = profile.department_id

        # Фильтрация преподавателей по выбранным факультету и кафедре
        if selected_faculty_id:
            teachers_qs = teachers_qs.filter(faculty_id=selected_faculty_id)
        if selected_department_id:
            teachers_qs = teachers_qs.filter(department_id=selected_department_id)

        # Получение выбранных объектов факультета и кафедры для отображения
        selected_faculty = next((f for f in visible_faculties if str(f.id) == str(selected_faculty_id)), None)
        selected_department = next((d for d in visible_departments if str(d.id) == str(selected_department_id)), None)

        # Сортировка и пагинация результатов
        teachers_qs = teachers_qs.order_by('user__last_name', 'user__first_name')
        paginator = Paginator(teachers_qs, 16)
        page_obj = paginator.get_page(request.GET.get('page'))

        # Возвращаем данные в шаблон
        return {
            'faculties': visible_faculties,
            'departments': visible_departments,
            'page_obj': page_obj,
            'selected_faculty_id': int(selected_faculty_id) if selected_faculty_id else None,
            'selected_department_id': int(selected_department_id) if selected_department_id else None,
            'selected_faculty': selected_faculty,
            'selected_department': selected_department,
            'is_superuser': is_superuser,
            'is_dean': is_dean,
            'is_viewer': is_viewer,
        }

def code_key(code):
    return [int(part) for part in code.split('.') if part.isdigit()]


class TeacherReportReadOnlyView(LoginRequiredMixin, TemplateView):
    template_name = 'main/view/teacher_reports_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # Кэширование редко меняющихся справочников
        years = cache.get_or_set('readonly_years', lambda: list(Year.objects.order_by('year')), 60*60)
        directions = cache.get_or_set('readonly_directions', lambda: list(Direction.objects.order_by('id')), 60*60)

        context['years'] = years
        context['directions'] = directions

        # Определяем год
        year_id = request.GET.get('year')
        if year_id:
            year = get_object_or_404(Year, id=year_id)
        else:
            year = years[-1] if years else None
        context['year'] = year

        # Определяем учителя
        teacher_id = request.GET.get('teacher')
        if teacher_id:
            teacher = get_object_or_404(User, id=teacher_id)
        else:
            teacher = request.user
        context['teacher'] = teacher

        if not year:
            return context

        # Загрузка всех MainIndicator и Indicator
        main_qs = MainIndicator.objects.filter(years=year).only('id', 'name', 'code', 'direction_id')
        indicators_qs = Indicator.objects.filter(years=year).only('id', 'main_indicator_id')

        # Группировка main по направлениям
        mains_by_dir = {}
        for m in main_qs:
            mains_by_dir.setdefault(m.direction_id, []).append(m)
        for dir_id, mis in mains_by_dir.items():
            mis.sort(key=lambda x: code_key(x.code))

        # Группировка indicators по main
        inds_by_main = {}
        for ind in indicators_qs:
            inds_by_main.setdefault(ind.main_indicator_id, []).append(ind)

        # Единоразовая выборка отчетов и агрегатов
        all_ind_ids = [ind.id for ind in indicators_qs]
        all_main_ids = [m.id for m in main_qs]

        tr_qs = TeacherReport.objects.filter(
            teacher=teacher,
            indicator_id__in=all_ind_ids,
            year=year
        ).select_related('indicator').prefetch_related('uploaded_works__co_authors')

        ai_qs = AggregatedIndicator.objects.filter(
            teacher=teacher,
            main_indicator_id__in=all_main_ids,
            year=year
        ).prefetch_related('uploaded_works__co_authors')

        # Словари для быстрого доступа
        tr_by_ind = {}
        for tr in tr_qs:
            tr_by_ind.setdefault(tr.indicator_id, []).append(tr)

        ai_by_main = {ai.main_indicator_id: ai for ai in ai_qs}

        aggregated_data = []
        for direction in directions:
            dir_mains = mains_by_dir.get(direction.id, [])
            dir_entry = {'direction': direction, 'main_indicators': []}

            for main in dir_mains:
                # Подготовка данных для main
                indicators = inds_by_main.get(main.id, [])

                # Сумма значений TeacherReport
                total = sum(
                    tr.value for ind in indicators for tr in tr_by_ind.get(ind.id, [])
                )

                # Агрегированный индикатор
                ai = ai_by_main.get(main.id)
                additional = ai.additional_value if ai else 0
                total += additional

                # Файлы aggregated
                uploaded_files = []
                if ai:
                    for f in ai.uploaded_works.all():
                        uploaded_files.append({
                            'file_name': f.file.name.split('/')[-1],
                            'author': teacher.get_full_name() or teacher.username,
                            'co_authors': [u.get_full_name() or u.username for u in f.co_authors.all()],
                            'uploaded_at': f.uploaded_at,
                        })
                    deadline = (
                        f"{_(calendar.month_name[ai.deadline_month])} {ai.deadline_year}"
                        if ai.deadline_month and ai.deadline_year else "—"
                    )
                else:
                    deadline = "—"

                # TeacherReport с файлами
                teacher_reports = []
                for ind in indicators:
                    for tr in tr_by_ind.get(ind.id, []):
                        files = []
                        for f in tr.uploaded_works.all():
                            files.append({
                                'file_url': f.file.url,
                                'file_name': f.file.name.split('/')[-1],
                                'author': teacher.get_full_name() or teacher.username,
                                'co_authors': [u.get_full_name() or u.username for u in f.co_authors.all()],
                                'uploaded_at': f.uploaded_at,
                            })
                        tr.uploaded_file_data = files
                        tr.deadline_display = (
                            f"{_(calendar.month_name[tr.deadline_month])} {tr.deadline_year}"
                            if tr.deadline_month and tr.deadline_year else "—"
                        )
                        teacher_reports.append(tr)

                dir_entry['main_indicators'].append({
                    'main_indicator': main,
                    'total_value': total,
                    'additional_value': additional,
                    'teacher_reports': teacher_reports,
                    'uploaded_works': uploaded_files,
                    'deadline_display': deadline,
                })

            aggregated_data.append(dir_entry)

        context['aggregated_data'] = aggregated_data
        return context

class ReportDepartmentView(LoginRequiredMixin, TemplateView):
    """
    Страница для заместителя заведующего кафедрой.
    Отображаются только кафедры, к которым он/она относится.
    Значения всех преподавателей по каждой кафедре суммируются.
    """

    template_name = 'main/view/report_department.html'

    def get_context_data(self, **kwargs):
        request = self.request
        user = request.user
        # 1. Профиль
        try:
            profile = user.profile
        except:
            return redirect('home')

        # 2. Выбор и кэширование года
        year_id = request.GET.get('year')
        if year_id:
            selected_year = get_object_or_404(Year, id=year_id)
        else:
            selected_year = cache.get_or_set(
                'dept_latest_year', lambda: Year.objects.latest('year'), 60*60)
        years = cache.get_or_set(
            'dept_years', lambda: list(Year.objects.all().order_by('-year')), 60*60)

        # 3. Определение доступных факультетов и кафедр
        all_faculties = cache.get_or_set(
            'dept_all_faculties',
            lambda: list(Faculty.objects.all().only('id','name')), 60*60
        )
        all_departments = cache.get_or_set(
            'dept_all_departments',
            lambda: list(Department.objects.all().only('id','name','faculty_id')), 60*60
        )

        if user.is_superuser:
            visible_faculties = all_faculties
            visible_departments = all_departments
        elif profile.role == 'viewer':
            visible_faculties = [f for f in all_faculties if f.id == profile.faculty_id]
            visible_departments = [d for d in all_departments if d.id == profile.department_id]
        else:
            return super().render_to_response({'no_permission': True})

        # 4. Считываем фильтры
        faculty_ids = request.GET.getlist('faculties') or [str(f.id) for f in visible_faculties]
        department_ids = request.GET.getlist('departments') or [str(d.id) for d in visible_departments]
        faculty_ids = [fid for fid in faculty_ids if fid != 'all']
        department_ids = [did for did in department_ids if did != 'all']

        selected_faculties = [f for f in visible_faculties if str(f.id) in faculty_ids]
        selected_departments = [d for d in visible_departments if str(d.id) in department_ids]

        # 5. Загрузка классификаторов
        directions = cache.get_or_set(
            'dept_directions',
            lambda: list(Direction.objects.all().only('id','name')), 60*60
        )
        main_qs = MainIndicator.objects.filter(
            direction__in=directions, years=selected_year
        ).only('id','code','name','unit','direction_id')
        ind_qs = Indicator.objects.filter(
            years=selected_year
        ).only('id','main_indicator_id','code','name','unit')

        # Группировка
        mains_by_direction = {}
        for m in main_qs:
            mains_by_direction.setdefault(m.direction_id, []).append(m)
        subs_by_main = {}
        for ind in ind_qs:
            subs_by_main.setdefault(ind.main_indicator_id, []).append(ind)

        # 6. Загрузка данных отчетов и агрегатов
        tr_qs = TeacherReport.objects.filter(
            year=selected_year,
            indicator__in=ind_qs,
            teacher__profile__department__in=selected_departments
        ).select_related('indicator','teacher').prefetch_related('uploaded_works')
        tr_by_sub = {}
        for tr in tr_qs:
            tr_by_sub.setdefault(tr.indicator_id, []).append(tr)

        ai_qs = AggregatedIndicator.objects.filter(
            year=selected_year,
            main_indicator__in=main_qs,
            teacher__profile__department__in=selected_departments
        ).select_related('main_indicator','teacher').prefetch_related('uploaded_works')
        ai_by_main = {}
        for ai in ai_qs:
            ai_by_main.setdefault(ai.main_indicator_id, []).append(ai)

        # 7. Формирование данных для шаблона
        data = []
        for d in directions:
            mains = mains_by_direction.get(d.id, [])
            dir_entry = {'name': d.name, 'main_indicators': []}
            for m in mains:
                has_sub = m.id in subs_by_main
                entry = {
                    'code': m.code, 'name': m.name, 'unit': m.unit,
                    'has_sub': has_sub, 'sub_indicators': [],
                    'teachers': [], 'total': 0
                }
                if has_sub:
                    subs = subs_by_main[m.id]
                    subtotal = 0
                    for sub in subs:
                        trs = tr_by_sub.get(sub.id, [])
                        tlist = [(tr.teacher.get_full_name(), tr.value, tr.uploaded_works.count())
                                 for tr in trs if tr.value > 0]
                        stot = sum(tr.value for tr in trs)
                        entry['sub_indicators'].append({
                            'code': sub.code, 'name': sub.name,
                            'unit': sub.unit, 'teachers': tlist, 'total': stot
                        })
                        subtotal += stot
                    entry['total'] = subtotal
                else:
                    ais = ai_by_main.get(m.id, [])
                    tlist = [(ai.teacher.get_full_name(), ai.additional_value, ai.uploaded_works.count())
                             for ai in ais if ai.additional_value > 0]
                    atot = sum(ai.additional_value for ai in ais)
                    entry['teachers'] = tlist
                    entry['total'] = atot
                dir_entry['main_indicators'].append(entry)
            data.append(dir_entry)

        # 8. Собираем контекст
        return {
            'years': years,
            'selected_year': selected_year,
            'data': data,
            'faculties': visible_faculties,
            'departments': visible_departments,
            'selected_faculties': [f.id for f in selected_faculties],
            'selected_departments': [d.id for d in selected_departments],
            'department_map': {
                f.id: [{'id': d.id, 'name': d.name} for d in visible_departments if d.faculty_id == f.id]
                for f in visible_faculties
            }
        }


@method_decorator(login_required, name='dispatch')
class DeanReportView(View):
    template_name = 'main/view/dean_report.html'

    def get(self, request):
        # 1. Выбор года и кэширование списка годов
        year_id = request.GET.get('year')
        if year_id:
            selected_year = get_object_or_404(Year, id=year_id)
        else:
            selected_year = cache.get_or_set('latest_year_dean', lambda: Year.objects.latest('year'), 60*60)

        years = cache.get_or_set('years_list_dean', lambda: list(Year.objects.all().order_by('-year')), 60*60)

        # 2. Профиль, факультет, кафедры и направления
        profile = request.user.profile
        faculty = profile.faculty
        departments = list(Department.objects.filter(faculty=faculty).only('id', 'name'))
        directions = cache.get_or_set('directions_list_dean', lambda: list(Direction.objects.all()), 60*60)

        # 3. Основные и подиндикаторы для выбранного года
        main_qs = MainIndicator.objects.filter(years=selected_year).only('id', 'name', 'code', 'direction_id')
        subs_qs = Indicator.objects.filter(years=selected_year).only('id', 'main_indicator_id', 'name')

        # Группировка основных индикаторов по направлениям
        mains_by_dir = {}
        for m in main_qs:
            mains_by_dir.setdefault(m.direction_id, []).append(m)
        for dir_id, mis in mains_by_dir.items():
            mis.sort(key=lambda x: [int(p) for p in x.code.split('.') if p.isdigit()])

        # Группировка подиндикаторов по основным
        subs_by_main = {}
        for s in subs_qs:
            subs_by_main.setdefault(s.main_indicator_id, []).append(s)

        # 4. Загрузка всех отчетов учителей и агрегатов одним запросом
        all_sub_ids = [s.id for s in subs_qs]
        all_main_ids = [m.id for m in main_qs]

        tr_qs = TeacherReport.objects.filter(
            year=selected_year,
            indicator_id__in=all_sub_ids,
            teacher__profile__department__in=departments
        ).select_related(
            'indicator', 'teacher', 'teacher__profile', 'teacher__profile__department'
        ).prefetch_related('uploaded_works')

        ai_qs = AggregatedIndicator.objects.filter(
            year=selected_year,
            main_indicator_id__in=all_main_ids,
            teacher__profile__department__in=departments
        ).select_related(
            'main_indicator', 'teacher', 'teacher__profile', 'teacher__profile__department'
        ).prefetch_related('uploaded_works')

        # Группировка отчетов по (sub_id, dept_id)
        tr_by_sub_dept = {}
        for tr in tr_qs:
            key = (tr.indicator_id, tr.teacher.profile.department_id)
            tr_by_sub_dept.setdefault(key, []).append(tr)

        # Группировка агрегатов по (main_id, dept_id)
        ai_by_main_dept = {}
        for ai in ai_qs:
            key = (ai.main_indicator_id, ai.teacher.profile.department_id)
            ai_by_main_dept.setdefault(key, []).append(ai)

        # 5. Сбор данных для каждого направления
        data = []
        for direction in directions:
            dir_mains = mains_by_dir.get(direction.id, [])
            dir_entry = {'name': direction.name, 'main_indicators': []}

            for main in dir_mains:
                mi = {'main': main, 'has_sub': main.id in subs_by_main,
                      'summary_row': [], 'sub_indicators': [], 'row': []}

                if mi['has_sub']:
                    subs = subs_by_main[main.id]
                    for dept in departments:
                        total = 0
                        teachers = set()
                        for sub in subs:
                            for tr in tr_by_sub_dept.get((sub.id, dept.id), []):
                                total += tr.value
                                teachers.add(tr.teacher.get_full_name())
                        mi['summary_row'].append({'value': total, 'teachers': list(teachers)})

                    for sub in subs:
                        sub_list = []
                        for dept in departments:
                            trs = tr_by_sub_dept.get((sub.id, dept.id), [])
                            val = sum(tr.value for tr in trs)
                            teachers = []
                            for tr in trs:
                                dl = f"{calendar.month_name[tr.deadline_month]} {tr.deadline_year}" if tr.deadline_month and tr.deadline_year else ''
                                teachers.append({
                                    'name': tr.teacher.get_full_name(),
                                    'value': tr.value,
                                    'file_count': tr.uploaded_works.count(),
                                    'deadline': dl,
                                })
                            sub_list.append({'value': val, 'teachers': teachers})
                        mi['sub_indicators'].append((sub, sub_list))
                else:
                    for dept in departments:
                        ais = ai_by_main_dept.get((main.id, dept.id), [])
                        total = sum(ai.additional_value for ai in ais)
                        teachers = []
                        for ai in ais:
                            dl = f"{calendar.month_name[ai.deadline_month]} {ai.deadline_year}" if ai.deadline_month and ai.deadline_year else ''
                            teachers.append({
                                'name': ai.teacher.get_full_name(),
                                'value': ai.additional_value,
                                'file_count': ai.uploaded_works.count(),
                                'deadline': dl,
                            })
                        mi['row'].append({'value': total, 'teachers': teachers})

                dir_entry['main_indicators'].append(mi)
            data.append(dir_entry)

        return render(request, self.template_name, {
            'faculty': faculty,
            'departments': departments,
            'data': data,
            'year': selected_year,
            'years': years,
        })
