from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from user.models import Profile, Faculty
from .models import TeacherReport, AggregatedIndicator, Year, Direction, MainIndicator, Indicator
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum

@login_required
def teachers_by_faculty(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return redirect('home')  # или куда-нибудь, если профиля нет

    # Проверка роли
    if profile.role != 'viewer':
        return render(request, 'main/view/no_permission.html')  # отдельная страница с сообщением

    faculties = Faculty.objects.all()
    selected_faculty_id = request.GET.get('faculty')

    if selected_faculty_id:
        teachers = Profile.objects.filter(role='teacher', faculty_id=selected_faculty_id)
    else:
        teachers = Profile.objects.filter(role='teacher')

    return render(request, 'main/view/list_teacher.html', {
        'faculties': faculties,
        'teachers': teachers,
        'selected_faculty_id': int(selected_faculty_id) if selected_faculty_id else None
    })


class TeacherReportReadOnlyView(LoginRequiredMixin, TemplateView):
    template_name = 'main/view/teacher_reports_list.html'

    def get(self, request, *args, **kwargs):
        direction_id = request.GET.get('direction')
        year_id = request.GET.get('year')
        teacher_id = request.GET.get('teacher')  # 👈 Получаем айди учителя из GET-параметра

        if not direction_id or not year_id:
            return super().get(request, *args, **kwargs)

        # Сохраняем выбранные значения
        self.direction = get_object_or_404(Direction, id=direction_id)
        self.year = get_object_or_404(Year, id=year_id)

        # 👇 Получаем выбранного учителя или текущего пользователя
        if teacher_id:
            self.teacher = get_object_or_404(User, id=teacher_id)
        else:
            self.teacher = request.user

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        direction_id = self.request.GET.get('direction')
        year_id = self.request.GET.get('year')

        directions = Direction.objects.all()
        years = Year.objects.all().order_by('year')

        context['directions'] = directions
        context['years'] = years

        if not direction_id or not year_id:
            return context  # Форма ещё не отправлена

        teacher = self.teacher
        direction = self.direction
        year = self.year

        main_indicators = MainIndicator.objects.filter(direction=direction, years=year)
        aggregated_data = []

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

            aggregated_data.append({
                'main_indicator': main_indicator,
                'total_value': total_value,
                'additional_value': additional_value,
                'teacher_reports': teacher_reports
            })

        context.update({
            'teacher': teacher,  # 👈 Не забываем передать учителя в контекст
            'direction': direction,
            'year': year,
            'aggregated_data': aggregated_data
        })

        return context


