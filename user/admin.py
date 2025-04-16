from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Faculty, Department, Profile


class ProfileInline(admin.StackedInline):  # или TabularInline для компактного вида
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fk_name = 'user'
    fields = ('role', 'faculty', 'department', 'phone')  # Только нужные поля


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'get_faculty', 'get_department')  # показываем роль/факультет
    list_select_related = ('profile',)  # оптимизация запросов

    def get_role(self, instance):
        return instance.profile.role
    get_role.short_description = 'Роль'

    def get_faculty(self, instance):
        return instance.profile.faculty
    get_faculty.short_description = 'Факультет'

    def get_department(self, instance):
        return instance.profile.department
    get_faculty.short_description = 'Кафедра'

    # Фильтры и поиск по профилю
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('profile')

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

admin.site.register(Faculty)
admin.site.register(Department)
