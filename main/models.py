from django.db import models
from django.contrib.auth.models import User
from calendar import month_name


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
    level = "деңгейі" , "деңгейі"
    quant = "саны (қолданыстағыларға қосымша)", "саны (қолданыстағыларға қосымша)"
    OPK = "ОПҚ санынан %", "ОПҚ санынан %"
    total = "Жалпы санынан %" , "Жалпы санынан %"



class MainIndicator(models.Model):
    """Главный индикатор, объединяющий несколько индикаторов"""
    code = models.CharField(max_length=15, default="", verbose_name="Код: ")
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name="Название главного индикатора")
    years = models.ManyToManyField(Year, verbose_name="Годы действия")
    unit = models.CharField(max_length=255, verbose_name="Единица измерения", choices=UnitChoices.choices,
                            default=UnitChoices.Quantity)
    points = models.IntegerField(verbose_name="Количество баллов", default=0)


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
    points = models.IntegerField(verbose_name="Количество баллов", default=0)


    def __str__(self):
        years_list = ", ".join(str(year.year) for year in self.years.all())  # Получаем все года
        return f" {self.code} {self.name} - ({years_list} - {self.unit})"


class SubSubIndicator(models.Model):
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE)
    code = models.CharField(max_length=15, default="", verbose_name="Код: ")
    years = models.ManyToManyField(Year, verbose_name="Годы действия")
    name = models.CharField(max_length=255, verbose_name="Название подподиндикатора: ")
    unit = models.CharField(max_length=255, verbose_name="Ед. изм. :" , choices=UnitChoices.choices, default=UnitChoices.Quantity)

    def __str__(self):
        return f"{self.code} — {self.name}"


class TeacherReport(models.Model):
    """Учитель вносит данные по индикатору"""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Учитель")
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, verbose_name="Индикатор")
    year = models.ForeignKey(Year, on_delete=models.CASCADE, verbose_name="Год")
    value = models.IntegerField(default=0, verbose_name="Подиндикатор")
    deadline_month = models.IntegerField(
        choices=[(i, month_name[i]) for i in range(1, 13)],
        null=True, blank=True,
        verbose_name="Месяц срока выполнения"
    )
    deadline_year = models.IntegerField(
        null=True, blank=True,
        verbose_name="Год срока выполнения"
    )


    class Meta:
        unique_together = ('teacher', 'indicator', 'year')

    def __str__(self):
        return f"{self.teacher} - {self.indicator.code} {self.indicator.name} | год - {self.year.year} |"

    def update_total_value(self):
        total = self.sub_indicator_values.aggregate(total=models.Sum('value'))['total'] or 0
        self.value = total
        self.save()


class AggregatedIndicator(models.Model):
    """Агрегированная модель для хранения суммы подиндикаторов у каждого учителя"""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Учитель")
    main_indicator = models.ForeignKey(MainIndicator, on_delete=models.CASCADE, related_name="aggregated_data", verbose_name="Главный индикатор")
    year = models.ForeignKey(Year, on_delete=models.CASCADE, verbose_name="Год")
    total_value = models.IntegerField(default=0, verbose_name="Сумма подиндикаторов")
    additional_value = models.IntegerField(default=0, verbose_name="Дополнительное значение")  # Можно использовать для других расчетов
    deadline_month = models.IntegerField(
        choices=[(i, month_name[i]) for i in range(1, 13)],
        null=True, blank=True,
        verbose_name="Месяц срока выполнения"
    )
    deadline_year = models.IntegerField(
        null=True, blank=True,
        verbose_name="Год срока выполнения"
    )


    class Meta:
        unique_together = ('teacher', 'main_indicator', 'year')  # исправлено

    def __str__(self):
        return f"{self.teacher} - {self.main_indicator.code} {self.main_indicator.name} ({self.year.year}) - Сумма: {self.total_value}"


class UploadedWork(models.Model):
    """ Для подиндикаторов (подтверждение заданного плана) """
    report = models.ForeignKey(TeacherReport, on_delete=models.CASCADE, related_name="uploaded_works")
    file = models.FileField(upload_to="media/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    co_authors = models.ManyToManyField(User, blank=True, related_name="coauthored_uploaded_works")


    def __str__(self):
        return f"{self.report.teacher} | {self.report.indicator.name} | {self.report.year.year}"


class UploadedMainWork(models.Model):
    """ Для главных индикаторов """
    aggregated_report = models.ForeignKey(AggregatedIndicator, on_delete=models.CASCADE, related_name="uploaded_works")
    file = models.FileField(upload_to="media/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    co_authors = models.ManyToManyField(User, blank=True, related_name="coauthored_uploaded_main_works")


    def __str__(self):
        return f"{self.aggregated_report.teacher} | {self.aggregated_report.main_indicator.name} | {self.aggregated_report.year.year}"


class SubSubIndicatorValue(models.Model):
    """Значения подподиндикаторов в отчёте учителя"""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Учитель")
    report = models.ForeignKey(TeacherReport, on_delete=models.CASCADE, related_name="sub_indicator_values")
    year = models.ForeignKey(Year, on_delete=models.CASCADE, verbose_name="Год")
    indicator = models.ForeignKey(SubSubIndicator, on_delete=models.CASCADE, verbose_name="Индикатор")
    value = models.IntegerField(default=0, verbose_name="Значение")
    deadline_month = models.IntegerField(
        choices=[(i, month_name[i]) for i in range(1, 13)],
        null=True, blank=True,
        verbose_name="Месяц срока выполнения"
    )
    deadline_year = models.IntegerField(
        null=True, blank=True,
        verbose_name="Год срока выполнения"
    )

    def __str__(self):
        return f"{self.name} ({self.value})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.report.update_total_value()  # обновить сумму в TeacherReport


class SubUploadedWork(models.Model):
    """ Для подиндикаторов (подтверждение заданного плана) """
    report = models.ForeignKey(SubSubIndicatorValue, on_delete=models.CASCADE, related_name="uploaded_works")
    file = models.FileField(upload_to="media/")
    uploaded_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.report.teacher} | {self.report.indicator.name} | {self.report.year.year}"