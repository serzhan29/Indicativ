from django.contrib import admin
from django.utils.html import format_html
from .models import (Year, Direction, MainIndicator, Indicator, TeacherReport,
                     AggregatedIndicator, UploadedWork, UploadedMainWork, SubUploadedWork,
                     SubSubIndicator, SubSubIndicatorValue)
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
        # Возвращаем кортеж с id и строкой "id - name"
        return [(f.id, f"{f.id} - {f.name}") for f in Faculty.objects.all()]

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
        return [(d.id, f"{d.id} - {d.name}") for d in Department.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                teacher__profile__department__id=self.value()
            ).distinct()
        return queryset

class UploadedWorkInline(admin.TabularInline):
    model = UploadedWork
    extra = 0
    readonly_fields = ("uploaded_at",)
    fields = ("file", "uploaded_at", "co_authors")
    filter_horizontal = ("co_authors",)

    # Фильтрация соавторов по кафедре пользователя
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "co_authors":
            user = request.user
            if hasattr(user, "profile") and user.profile.department:
                department = user.profile.department
                kwargs["queryset"] = User.objects.filter(
                    profile__department=department
                ).order_by("last_name", "first_name")
            else:
                kwargs["queryset"] = User.objects.none()
        return super().formfield_for_manytomany(db_field, request, **kwargs)



class UploadedMainWorkInline(admin.TabularInline):
    model = UploadedMainWork
    extra = 0
    readonly_fields = ("uploaded_at",)
    fields = ("file", "uploaded_at", "co_authors")
    filter_horizontal = ("co_authors",)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "co_authors":
            user = request.user
            if hasattr(user, "profile") and user.profile.department:
                department = user.profile.department
                kwargs["queryset"] = User.objects.filter(
                    profile__department=department
                ).order_by("last_name", "first_name")
            else:
                kwargs["queryset"] = User.objects.none()
        return super().formfield_for_manytomany(db_field, request, **kwargs)



@admin.register(TeacherReport)
class TeacherReportAdmin(admin.ModelAdmin):
    list_display = (
        "teacher_info",
        "teacher",
        "short_indicator",
        "year",
        "highlight_value",
        "uploaded_file_count"
    )
    inlines = [UploadedWorkInline]
    search_fields = ("teacher__username", "indicator__name", "year__year")
    ordering = ("year", "teacher")

    def short_indicator(self, obj):
        name = obj.indicator.name
        code = obj.indicator.code
        short_name = name[:30] + "..." if len(name) > 30 else name
        return f"{code} - {short_name}"

    short_indicator.short_description = "Индикатор (код + имя)"

    short_indicator.short_description = "Индикатор (сокр.)"

    def indicator_code(self, obj):
        return obj.indicator.code

    indicator_code.short_description = "Код"

    def highlight_value(self, obj):
        color = "red" if obj.value == 0 else "green"
        return format_html(f'<span style="color: {color}; font-weight: bold;">{obj.value}</span>')

    highlight_value.short_description = "Значение"

    def uploaded_file_count(self, obj):
        return obj.uploaded_works.count()

    uploaded_file_count.short_description = "Файлы (шт.)"

    def teacher_info(self, obj):
        return f"{obj.teacher.last_name} {obj.teacher.first_name}"

    teacher_info.short_description = "Преподаватель"

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
        "teacher_info",
        "teacher",
        "short_main_indicator",
        "year",
        "total_value",
        "additional_value",
        "uploaded_main_file_count"
    )
    inlines = [UploadedMainWorkInline]
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
        code = obj.main_indicator.code
        name = obj.main_indicator.name
        short_name = name[:15] + "..." if len(name) > 15 else name
        return f"{code} - {short_name}"

    short_main_indicator.short_description = "Код и название"

    def uploaded_main_file_count(self, obj):
        return obj.uploaded_works.count()

    def teacher_info(self, obj):
        return f"{obj.teacher.last_name} {obj.teacher.first_name} "

    teacher_info.short_description = "Преподаватель"


    uploaded_main_file_count.short_description = "Файлы (шт.)"

class SubUploadedWorkInline(admin.TabularInline):
    model = SubUploadedWork
    extra = 0
    readonly_fields = ("uploaded_at",)


@admin.register(SubSubIndicator)
class SubSubIndicatorAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "indicator", "unit", "years_display")
    list_filter = ("indicator", "unit", "years")
    search_fields = ("name", "code", "indicator__name")

    def years_display(self, obj):
        return ", ".join(str(year.year) for year in obj.years.all())

    years_display.short_description = "Годы действия"


@admin.register(SubSubIndicatorValue)
class SubSubIndicatorValueAdmin(admin.ModelAdmin):
    list_display = (
        "teacher_info",
        "indicator",
        "value",
        "year",
        "deadline_month",
        "deadline_year",
        "uploaded_files_count",
    )
    list_filter = ("year", "deadline_year", "deadline_month", "indicator")
    search_fields = ("teacher__username", "teacher__last_name", "indicator__name")
    inlines = [SubUploadedWorkInline]

    def teacher_info(self, obj):
        profile = getattr(obj.teacher, "profile", None)
        if profile and profile.department and profile.department.faculty:
            return f"{obj.teacher.get_full_name()} ({profile.department.faculty.name} | {profile.department.name})"
        return obj.teacher.get_full_name()

    teacher_info.short_description = "Преподаватель"

    def uploaded_files_count(self, obj):
        return obj.uploaded_works.count()

    uploaded_files_count.short_description = "Файлов"


admin.site.register(UploadedMainWork)
