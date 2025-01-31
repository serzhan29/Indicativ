from django.db import models

class Direction(models.Model):
    """Направление"""
    name = models.CharField(max_length=255, verbose_name="Направление")

    def __str__(self):
        return self.name

class Year(models.Model):
    """Года"""
    year = models.IntegerField(verbose_name="Год")

    def __str__(self):
        return str(self.year)

class MainIndicator(models.Model):
    """Главный индикатор"""
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE, verbose_name="Направление")
    year = models.ForeignKey(Year, on_delete=models.CASCADE, verbose_name="Год")
    name = models.CharField(max_length=255, verbose_name="Название главного индикатора")
    value = models.IntegerField(default=0, verbose_name="Количество главного индикатора")
    total = models.IntegerField(default=0, verbose_name="Общее количество")

    def __str__(self):
        return f"{self.name} - {self.year}"

class SubIndicator(models.Model):
    """Подиндикатор"""
    main_indicator = models.ForeignKey(MainIndicator, on_delete=models.CASCADE, verbose_name="Главный индикатор")
    year = models.ForeignKey(Year, on_delete=models.CASCADE, verbose_name="Год")
    name = models.CharField(max_length=255, verbose_name="Название подиндикатора")
    value = models.IntegerField(default=0, verbose_name="Количество")

    def __str__(self):
        return self.name