from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Faculty, Department, Profile, VisitLog


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fk_name = 'user'
    fields = ('role', 'faculty', 'department', 'phone')


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'get_faculty', 'get_department')
    list_select_related = ('profile',)

    # 🔎 Фильтры по профилю
    list_filter = ('profile__role', 'profile__faculty', 'profile__department')

    def get_role(self, instance):
        return instance.profile.role
    get_role.short_description = 'Роль'

    def get_faculty(self, instance):
        return instance.profile.faculty
    get_faculty.short_description = 'Факультет'

    def get_department(self, instance):
        return instance.profile.department
    get_department.short_description = 'Кафедра'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('profile')


@admin.register(Faculty)
class CustomFacultyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')

@admin.register(Department)
class CustomDepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')


@admin.register(VisitLog)
class VisitLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'ip', 'path')
    list_filter = ('user', 'ip')
    search_fields = ('ip', 'path')
    list_display_links = ('user', 'ip', 'path')

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
