from django.db import models
from django.contrib.auth.models import User

class Year(models.Model):
    """Модель для хранения годов"""
    year = models.IntegerField(unique=True, verbose_name="Год")
    editable = models.BooleanField(default=True, verbose_name="Можно редактировать")

    def __str__(self):
        return str(self.year)


class Direction(models.Model):
    """Направления деятельности (например, Научные, Методические)"""
    name = models.CharField(max_length=100, verbose_name="Название направления")

    def __str__(self):
        return self.name


class MainIndicator(models.Model):
    """Главный индикатор, объединяющий несколько индикаторов"""
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name="Название главного индикатора")
    years = models.ManyToManyField(Year, verbose_name="Годы действия")


    def __str__(self):
        return f"{self.name} - {self.direction.name}"


class Indicator(models.Model):
    """Подчинённые индикаторы, принадлежащие главному индикатору"""
    main_indicator = models.ForeignKey(MainIndicator, on_delete=models.CASCADE, related_name="indicators", verbose_name="Главный индикатор")
    years = models.ManyToManyField(Year, verbose_name="Годы действия")
    name = models.CharField(max_length=255, verbose_name="Название индикатора")

    def __str__(self):
        years_list = ", ".join(str(year.year) for year in self.years.all())  # Получаем все года
        return f"{self.name} - ({years_list})"


class TeacherReport(models.Model):
    """Учитель вносит данные по индикатору"""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Учитель")
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, verbose_name="Индикатор")
    year = models.ForeignKey(Year, on_delete=models.CASCADE, verbose_name="Год")
    main_value = models.IntegerField(default=0, verbose_name="Главный индикатор")
    value = models.IntegerField(default=0, verbose_name="Подиндикатор")


    class Meta:
        unique_together = [['teacher', 'indicator', 'year']]

    def __str__(self):
        return f"{self.teacher} - {self.indicator.name} | year - {self.year}|"

