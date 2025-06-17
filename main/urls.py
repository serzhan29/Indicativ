from django.urls import path
from .views import  (DirectionListView, YearListView, TeacherReportView,
                     UpdateValueView, index, TeacherReportAllDirection,
                    update_deadline,FileDeleteView, FileModalView)
from .views_docx import (download_teacher_report,
                         TeacherReportWordExportView, export_report, export_department_report_docx)
from .observer import (TeachersByFacultyView, TeacherReportReadOnlyView,
                     ReportDepartmentView, get_departments, dean_report)

urlpatterns = [
    path('', DirectionListView.as_view(), name='direction_list'),
    path('main', index, name='index'),
    path('directions/<int:direction_id>/years/', YearListView.as_view(), name='choose_year'),

    path('download_teacher_report/<int:teacher_id>/<int:direction_id>/<int:year_id>/', download_teacher_report, name='download_teacher_report'),

    path('report/<int:direction_id>/<int:year_id>/', TeacherReportView.as_view(), name='teacher_report'),
    # Обновление значение
    path('update_value/', UpdateValueView.as_view(), name='update_value'),
    path('teacher/', TeachersByFacultyView.as_view(), name='teachers_by_faculty'),

    # Для учителей
    path('teacher/report/', TeacherReportReadOnlyView.as_view(), name='teacher_report_readonly'),
    path('teacher-report/download/', TeacherReportWordExportView.as_view(), name='teacher_report_download'),
    # Отчеты преподавателей
    path('report/department/', ReportDepartmentView.as_view(), name='report_department'),
    #Обновление значений
    path('update-deadline/', update_deadline, name='update_deadline'),
    # Загрузка файлов для соавторов и авторов
    path(
        'report/<int:report_id>/files/',
        FileModalView.as_view(),
        name='report_files'
    ),
    # 2) Удаление одного файла
    path(
        'report/file/<int:file_id>/delete/',
        FileDeleteView.as_view(),
        name='report_file_delete'
    ),

    path('full_teacher_report/', TeacherReportAllDirection.as_view(), name='teacher_full_report'),
    path('full_teacher_report/<int:year_id>/', TeacherReportAllDirection.as_view(),
         name='teacher_full_report_with_year'),

    # Для Декана
    path('dean_report/', dean_report, name='dean_report'),

    path('get_departments/<str:faculty_id>/', get_departments, name='get_departments'),
    path('export_report/<int:faculty_id>/', export_report, name='export_report'),
    path('report_value_department/<int:faculty_id>/', export_department_report_docx, name='export_department_report_docx'),
]


