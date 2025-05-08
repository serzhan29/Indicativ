from django.urls import path
from .views import  (DirectionListView, YearListView, TeacherReportView,
                     UpdateValueView, index, TeacherReportAllDirection)
from .views_docx import download_teacher_report, TeacherReportWordExportView, export_report, export_department_report_docx
from .observer import (teachers_by_faculty, TeacherReportReadOnlyView,
                     report_department, get_departments, observer_index, dean_report)

urlpatterns = [
    path('', DirectionListView.as_view(), name='direction_list'),
    path('main', index, name='index'),
    path('directions/<int:direction_id>/years/', YearListView.as_view(), name='choose_year'),
    path('download_teacher_report/<int:teacher_id>/<int:direction_id>/<int:year_id>/', download_teacher_report, name='download_teacher_report'),

    path('report/<int:direction_id>/<int:year_id>/', TeacherReportView.as_view(), name='teacher_report'),
    path('update_value/', UpdateValueView.as_view(), name='update_value'),

    path('teacher/', teachers_by_faculty, name='teachers_by_faculty'),

    path('teacher/report/', TeacherReportReadOnlyView.as_view(), name='teacher_report_readonly'),
    path('teacher-report/download/', TeacherReportWordExportView.as_view(), name='teacher_report_download'),
    path('report/department/', report_department, name='report_department'),
    path('dean_report/', dean_report, name='dean_report'),

    path('get_departments/<str:faculty_id>/', get_departments, name='get_departments'),
    path('export_report/<int:faculty_id>/', export_report, name='export_report'),
    path('report_value_department/<int:faculty_id>/', export_department_report_docx, name='export_department_report_docx'),
    path('observer_grahics/', observer_index, name='observer_index'),

    path('full_teacher_report/', TeacherReportAllDirection.as_view(), name='teacher_full_report'),
    path('full_teacher_report/<int:year_id>/', TeacherReportAllDirection.as_view(), name='teacher_full_report_with_year')

]


