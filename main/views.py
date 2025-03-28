import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Direction, Year, TeacherReport, Indicator, MainIndicator, AggregatedIndicator, User
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.views.generic import TemplateView


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


class TeacherReportView(LoginRequiredMixin, TemplateView):
    """Генерация отчетов для учителя и их агрегация"""
    template_name = 'main/teacher_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user
        direction = get_object_or_404(Direction, id=self.kwargs['direction_id'])
        year = get_object_or_404(Year, id=self.kwargs['year_id'])

        main_indicators = MainIndicator.objects.filter(direction=direction, years=year)
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

            aggregated_data.append({
                'id': aggregated_indicator.id,
                'main_indicator': main_indicator,
                'total_value': total_value,
                'additional_value': aggregated_indicator.additional_value,
                'teacher_reports': teacher_reports
            })

        context.update({
            'teacher': teacher,
            'direction': direction,
            'year': year,
            'aggregated_data': aggregated_data
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


