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


class UnitChoices(models.TextChoices):
    Quantity = "Саны", "Саны"
    Department = "Кафедрада оқылатын пәндердің үлесі ( % )", "Кафедрада оқылатын пәндердің үлесі ( % )"
    Percent = "%", "%"


class MainIndicator(models.Model):
    """Главный индикатор, объединяющий несколько индикаторов"""
    code = models.CharField(max_length=15, default="", verbose_name="Код: ")
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name="Название главного индикатора")
    years = models.ManyToManyField(Year, verbose_name="Годы действия")
    unit = models.CharField(max_length=255, verbose_name="Единица измерения", choices=UnitChoices.choices,
                            default=UnitChoices.Quantity)

    def __str__(self):
        return f"{self.code} {self.name} - {self.direction.name}"


class Indicator(models.Model):
    """Подчинённые индикаторы, принадлежащие главному индикатору"""
    main_indicator = models.ForeignKey(MainIndicator, on_delete=models.CASCADE, related_name="indicators", verbose_name="Главный индикатор")
    code = models.CharField(max_length=15, default="", verbose_name="Код: ")
    years = models.ManyToManyField(Year, verbose_name="Годы действия")
    name = models.CharField(max_length=255, verbose_name="Название индикатора")
    unit = models.CharField(max_length=255, verbose_name="Единица измерения", choices=UnitChoices.choices,
                            default=UnitChoices.Quantity)

    def __str__(self):
        years_list = ", ".join(str(year.year) for year in self.years.all())  # Получаем все года
        return f" {self.code} {self.name} - ({years_list} - {self.unit})"


class TeacherReport(models.Model):
    """Учитель вносит данные по индикатору"""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Учитель")
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, verbose_name="Индикатор")
    year = models.ForeignKey(Year, on_delete=models.CASCADE, verbose_name="Год")
    value = models.IntegerField(default=0, verbose_name="Подиндикатор")

    class Meta:
        unique_together = ('teacher', 'indicator', 'year')  # исправлено

    def __str__(self):
        return f"{self.teacher} - {self.indicator.code} {self.indicator.name} | год - {self.year.year} |"  # исправлено


class AggregatedIndicator(models.Model):
    """Агрегированная модель для хранения суммы подиндикаторов у каждого учителя"""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Учитель")
    main_indicator = models.ForeignKey(MainIndicator, on_delete=models.CASCADE, related_name="aggregated_data", verbose_name="Главный индикатор")
    year = models.ForeignKey(Year, on_delete=models.CASCADE, verbose_name="Год")
    total_value = models.IntegerField(default=0, verbose_name="Сумма подиндикаторов")
    additional_value = models.IntegerField(default=0, verbose_name="Дополнительное значение")  # Можно использовать для других расчетов

    class Meta:
        unique_together = ('teacher', 'main_indicator', 'year')  # исправлено

    def __str__(self):
        return f"{self.teacher} - {self.main_indicator.code} {self.main_indicator.name} ({self.year.year}) - Сумма: {self.total_value}"


class UploadedWork(models.Model):
    """ Для подиндикаторов (подтверждение заданного плана) """
    report = models.ForeignKey(TeacherReport, on_delete=models.CASCADE, related_name="uploaded_works")
    file = models.FileField(upload_to="uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.report.teacher} | {self.report.indicator.name} | {self.report.year.year}"


class UploadedMainWork(models.Model):
    """ Для главных индикаторов """
    aggregated_report = models.ForeignKey(AggregatedIndicator, on_delete=models.CASCADE, related_name="uploaded_works")
    file = models.FileField(upload_to="main_indicator_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.aggregated_report.teacher} | {self.aggregated_report.main_indicator.name} | {self.aggregated_report.year.year}"
