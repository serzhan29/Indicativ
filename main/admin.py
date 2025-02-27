from django.contrib import admin
from django.utils.html import format_html
from .models import Year, Direction, MainIndicator, Indicator, TeacherReport


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
    list_display = ("short_name", "direction", "display_years")
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
    list_display = ("name", "short_main_indicator", "display_years")  # Используем сокращенное название
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



@admin.register(TeacherReport)
class TeacherReportAdmin(admin.ModelAdmin):
    list_display = ("teacher", "short_indicator", "year", "main_value", "highlight_value")
    search_fields = ("teacher__username", "indicator__name", "year__year")
    list_filter = ("teacher", "year", "short_indicator_filter")
    ordering = ("year", "teacher")

    def short_indicator(self, obj):
        """Сокращает название индикатора, если оно длиннее 30 символов"""
        return obj.indicator.name[:30] + "..." if len(obj.indicator.name) > 30 else obj.indicator.name

    short_indicator.short_description = "Индикатор (сокр.)"

    def highlight_value(self, obj):
        """Отображает значение отчета, подсвечивая его красным, если оно равно 0"""
        color = "red" if obj.value == 0 else "green"
        return format_html(f'<span style="color: {color}; font-weight: bold;">{obj.value}</span>')

    highlight_value.short_description = "Значение"

    # Кастомный фильтр для сокращенных индикаторов
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

    list_filter = ("teacher", "year", ShortIndicatorFilter)  # Используем кастомный фильтр

