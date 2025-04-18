from django.contrib import admin
from django.utils.html import format_html
from .models import Year, Direction, MainIndicator, Indicator, TeacherReport, AggregatedIndicator
from user.models import User, Department, Faculty


@admin.register(Year)
class YearAdmin(admin.ModelAdmin):
    list_display = ("year", "editable")
    list_editable = ("editable",)  # Позволяет менять значение прямо в списке
    ordering = ("year",)


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ("id", "name",)
    ordering = ("id",)


@admin.register(MainIndicator)
class MainIndicatorAdmin(admin.ModelAdmin):
    list_display = ( "code", "short_name", "direction", "display_years")
    list_display_links = ("code", "short_name",)
    search_fields = ("name", "direction__name")
    list_filter = ("direction", "years")
    ordering = ("direction", "name")

    def short_name(self, obj):
        """Сокращает название главного индикатора, если оно слишком длинное"""
        return obj.name[:30] + "..." if len(obj.name) > 30 else obj.name

    short_name.short_description = "Название (сокр.)"

    def display_years(self, obj):
        return ", ".join(str(year.year) for year in obj.years.all())

    display_years.short_description = "Годы действия"


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ( "code", "name", "short_main_indicator", "display_years")  # Используем сокращенное название
    list_display_links = ("code", "name")
    search_fields = ("name", "main_indicator__name")
    list_filter = ("years", "short_main_indicator_filter")  # Добавляем кастомный фильтр
    ordering = ("main_indicator", "name")

    def short_main_indicator(self, obj):
        """Сокращает название главного индикатора в списке, если оно длиннее 30 символов"""
        return obj.main_indicator.name[:30] + "..." if len(obj.main_indicator.name) > 30 else obj.main_indicator.name

    short_main_indicator.short_description = "Главный индикатор (сокр.)"

    def display_years(self, obj):
        return ", ".join(str(year.year) for year in obj.years.all())

    display_years.short_description = "Годы действия"

    # Кастомный фильтр для сокращенных названий главных индикаторов
    class ShortMainIndicatorFilter(admin.SimpleListFilter):
        title = "Главный индикатор (сокр.)"
        parameter_name = "main_indicator"

        def lookups(self, request, model_admin):
            indicators = MainIndicator.objects.all()
            return [
                (indicator.id, indicator.name[:30] + "..." if len(indicator.name) > 30 else indicator.name)
                for indicator in indicators
            ]

        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(main_indicator__id=self.value())
            return queryset

    list_filter = ("years", ShortMainIndicatorFilter)  # Используем кастомный фильтр


# === Кастомный фильтр по факультету ===
class FacultyFilter(admin.SimpleListFilter):
    title = "Факультет"
    parameter_name = "faculty"

    def lookups(self, request, model_admin):
        return [(f.id, f.name) for f in Faculty.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                teacher__profile__department__faculty__id=self.value()
            ).distinct()
        return queryset

# === Кастомный фильтр по кафедре ===
class DepartmentFilter(admin.SimpleListFilter):
    title = "Кафедра"
    parameter_name = "department"

    def lookups(self, request, model_admin):
        return [(d.id, d.name) for d in Department.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                teacher__profile__department__id=self.value()
            ).distinct()
        return queryset

@admin.register(TeacherReport)
class TeacherReportAdmin(admin.ModelAdmin):
    list_display = ("teacher", "short_indicator", "year", "highlight_value")
    search_fields = ("teacher__username", "indicator__name", "year__year")
    ordering = ("year", "teacher")

    def short_indicator(self, obj):
        return obj.indicator.name[:30] + "..." if len(obj.indicator.name) > 30 else obj.indicator.name

    short_indicator.short_description = "Индикатор (сокр.)"

    def highlight_value(self, obj):
        color = "red" if obj.value == 0 else "green"
        return format_html(f'<span style="color: {color}; font-weight: bold;">{obj.value}</span>')

    highlight_value.short_description = "Значение"

    class ShortIndicatorFilter(admin.SimpleListFilter):
        title = "Индикатор (сокр.)"
        parameter_name = "indicator"

        def lookups(self, request, model_admin):
            indicators = Indicator.objects.all()
            return [
                (indicator.id, indicator.name[:30] + "..." if len(indicator.name) > 30 else indicator.name)
                for indicator in indicators
            ]

        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(indicator__id=self.value())
            return queryset

    list_filter = (
        "teacher",
        "year",
        ShortIndicatorFilter,
        FacultyFilter,
        DepartmentFilter,
    )


# === Регистрация модели AggregatedIndicator ===
@admin.register(AggregatedIndicator)
class AggregatedIndicatorAdmin(admin.ModelAdmin):
    list_display = (
        "teacher",
        "short_main_indicator",
        "year",
        "total_value",
        "additional_value"
    )
    list_filter = (
        "year",
        "teacher",
        "main_indicator__direction",
        FacultyFilter,
        DepartmentFilter,
    )
    search_fields = (
        "teacher__username",
        "teacher__first_name",
        "teacher__last_name",
        "main_indicator__name",
        "year__year"
    )
    ordering = ("year", "teacher")

    def short_main_indicator(self, obj):
        return obj.main_indicator.name[:15] + "..." if len(obj.main_indicator.name) > 15 else obj.main_indicator.name

    short_main_indicator.short_description = "Главн. индикатор"