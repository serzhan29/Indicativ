from django.urls import path
from .views import choose_direction, choose_year, teacher_report, update_value
from .views_docx import download_teacher_report
from .views_display import reports_dashboard, update_report2

urlpatterns = [
    path('', choose_direction, name='direction_list'),
    path('report/<int:direction_id>/', choose_year, name='choose_year'),
    path('download_teacher_report/<int:direction_id>/<int:year_id>/', download_teacher_report, name='download_teacher_report'),


    path('reports/teacher/<int:direction_id>/<int:year_id>/', teacher_report, name='teacher_report'),
    path('update_value/', update_value, name='update_value'),

]


