from django.urls import path
from .views import choose_direction, choose_year, update_report, teacher_report

urlpatterns = [
    path('', choose_direction, name='direction_list'),
    path('reports/<int:direction_id>/', choose_year, name='choose_year'),
    path('reports/<int:direction_id>/<int:year_id>/', teacher_report, name='view_teacher_report'),
    path('update-report/', update_report, name='update_report'),
]

