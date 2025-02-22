from django.contrib import admin
from .models import Year, Direction, TeacherReport, MainIndicator, Indicator

admin.site.register(Year)
admin.site.register(Direction)

class MainIndicatorAdmin(admin.ModelAdmin):
    list_display = ('name', )  # Отображаем название, направление и годы


admin.site.register(MainIndicator, MainIndicatorAdmin)

admin.site.register(Indicator)

admin.site.register(TeacherReport)