from django.urls import path
from .views import choose_direction, choose_year, update_report, teacher_report
from .views_docx import generate_word_report
from .views_display import reports_dashboard, update_report2

urlpatterns = [
    path('', choose_direction, name='direction_list'),
    path('report/<int:direction_id>/', choose_year, name='choose_year'),
    path('report/<int:direction_id>/<int:year_id>/', teacher_report, name='view_teacher_report'),
    path('update-report/', update_report, name='update_report'),
    path('download_report/<int:direction_id>/<int:year_id>/', generate_word_report, name='download_report'),

    path('report/', reports_dashboard, name='reports_dashboard'),  # Без параметров
    path('report/<int:direction_id>/<int:year_id>/', reports_dashboard, name='reports_dashboard'),
    path('report/update2/', update_report2, name='update_report2'),  # AJAX-запрос на обновление отчета
]


