from django.urls import path
from .views import  DirectionListView, YearListView, TeacherReportView, UpdateValueView
from .views_docx import download_teacher_report
from .views_display import reports_dashboard, update_report2

urlpatterns = [
    path('', DirectionListView.as_view(), name='direction_list'),
    path('directions/<int:direction_id>/years/', YearListView.as_view(), name='choose_year'),
    path('download_teacher_report/<int:direction_id>/<int:year_id>/', download_teacher_report, name='download_teacher_report'),

    path('report/<int:direction_id>/<int:year_id>/', TeacherReportView.as_view(), name='teacher_report'),
    path('update_value/', UpdateValueView.as_view(), name='update_value'),

]


