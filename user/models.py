from django.db import models
from django.contrib.auth.models import User
from smart_selects.db_fields import ChainedForeignKey
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class Faculty(models.Model):
    """Факультеты"""
    name = models.CharField(max_length=100, verbose_name=_("Название факультета"))

    def __str__(self):
        return self.name

class Department(models.Model):
    """Кафедра, привязанная к факультету"""
    name = models.CharField(max_length=100, verbose_name=_("Название кафедры"))
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="departments", verbose_name="Факультет")

    def __str__(self):
        return f"{self.name} - ({self.faculty.name})"


class Profile(models.Model):
    """Дополнительные данные пользователя"""

    ROLES = (
        ('teacher', 'Мұғалім'),
        ('viewer', 'Қараушы'),
        ('dean', 'Декан'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    role = models.CharField(max_length=10, choices=ROLES, default='viewer', verbose_name="Роль")
    faculty = models.ForeignKey('Faculty', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Факультет")
    department = ChainedForeignKey(
        'user.Department',
        chained_field="faculty",
        chained_model_field="faculty",
        show_all=False,
        auto_choose=True,
        sort=True,
        verbose_name="Кафедра",
        null=True,
        blank=True
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    father_name = models.CharField(max_length=100, blank=True, verbose_name="Отчество")
    photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True, verbose_name="Фото")

    def clean(self):
        email = self.user.email
        if email and not email.endswith('@ayu.edu.kz'):
            raise ValidationError("Email должен оканчиваться на @ayu.edu.kz")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class VisitLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip = models.GenericIPAddressField()
    path = models.CharField(max_length=500)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user or 'Anonymous'} | {self.ip} | {self.path}"