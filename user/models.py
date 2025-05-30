from django.db import models
from django.contrib.auth.models import User
from smart_selects.db_fields import ChainedForeignKey


class Faculty(models.Model):
    """Факультеты"""
    name = models.CharField(max_length=100, verbose_name="Название факультета")

    def __str__(self):
        return self.name

class Department(models.Model):
    """Кафедра, привязанная к факультету"""
    name = models.CharField(max_length=100, verbose_name="Название кафедры")
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="departments", verbose_name="Факультет")

    def __str__(self):
        return f"{self.name} ({self.faculty.name})"


class Profile(models.Model):
    """Дополнительные данные пользователя"""
    ROLES = (
        ('teacher', 'Мұғалім'),
        ('viewer', 'Қараушы'),
        ('dean', 'Декан'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    role = models.CharField(max_length=10, choices=ROLES, default='viewer', verbose_name="Роль")
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Факультет")
    department = ChainedForeignKey(
        'user.Department',
        chained_field="faculty",
        chained_model_field="faculty",
        show_all=False, auto_choose=True, sort=True,
        verbose_name="Кафедра",null=True,blank=True
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"