from django.db import models
from django.contrib.auth.models import User



class Direction(models.Model):
    """Направления деятельности (например, Научные, Методические)"""
    name = models.CharField(max_length=100, verbose_name="Название направления")

    def __str__(self):
        return self.name


class Year(models.Model):
    """Учебные года (2023, 2024 и т.д.)"""
    year = models.IntegerField(unique=True, verbose_name="Год")

    def __str__(self):
        return str(self.year)


class MainIndicator(models.Model):
    """Главный индикатор"""
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE, verbose_name="Направление")
    years = models.ManyToManyField(Year, verbose_name="Годы действия")
    name = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")

    # Автоматически рассчитываемое поле (можно заменить на сигнал)
    total = models.IntegerField(default=0, verbose_name="Суммарное значение")

    def __str__(self):
        return f"{self.name} ({self.direction})"


class SubIndicator(models.Model):
    """Под-индикатор"""
    main_indicator = models.ForeignKey(MainIndicator, on_delete=models.CASCADE, verbose_name="Главный индикатор")
    year = models.ForeignKey(Year, on_delete=models.CASCADE, verbose_name="Год")
    name = models.CharField(max_length=200, verbose_name="Название")
    default_value = models.IntegerField(default=0, verbose_name="Значение по умолчанию")

    def __str__(self):
        return f"{self.name} ({self.year})"


class TeacherReport(models.Model):
    """Отчет учителя"""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Учитель")
    sub_indicator = models.ForeignKey(SubIndicator, on_delete=models.CASCADE, verbose_name="Под-индикатор")
    custom_value = models.IntegerField(default=0, verbose_name="Значение учителя")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        unique_together = [['teacher', 'sub_indicator']]

    def __str__(self):
        return f"{self.teacher} - {self.sub_indicator}"