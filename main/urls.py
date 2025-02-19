from django.urls import path
from . import views


urlpatterns = [
    path('', views.direction_list, name='direction_list'),
    path('years/<int:direction_id>/', views.year_list, name='year_list'),
    path('reports/<int:direction_id>/<int:year>/', views.report_list, name='report_list'),
    path('report/<int:report_id>/', views.report_detail, name='report_detail'),
]