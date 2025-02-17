from django.contrib import admin
from .models import Year, Direction, TeacherReport, MainIndicator, SubIndicator


class MainIndicatorAdmin(admin.ModelAdmin):
    list_display = ('name', 'direction', 'get_years')  # Отображаем название, направление и годы
    filter_horizontal = ('years',)  # Удобный выбор годов в ManyToManyField

    def get_years(self, obj):
        return ", ".join([str(year.year) for year in obj.years.all()])  # Показываем все связанные годы
    get_years.short_description = "Годы"

admin.site.register(MainIndicator, MainIndicatorAdmin)

admin.site.register(Year)
admin.site.register(Direction)
admin.site.register(TeacherReport)
admin.site.register(SubIndicator)