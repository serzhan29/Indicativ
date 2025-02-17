from django.db import models
from django.contrib.auth.models import User


class Faculty(models.Model):
    """Факультеты"""
    name = models.CharField(max_length=100, verbose_name="Название факультета")

    def __str__(self):
        return self.name

class Profile(models.Model):
    """Дополнительные данные пользователя"""
    ROLES = (
        ('teacher', 'Учитель'),
        ('viewer', 'Просматривающий'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    role = models.CharField(max_length=10, choices=ROLES, default='viewer', verbose_name="Роль")
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Факультет")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"