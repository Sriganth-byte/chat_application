from django.urls import path
from . import views

urlpatterns = [
    path('', views.ReportView.as_view(), name='create-report'),
    path('mine/', views.MyReportsView.as_view(), name='my-reports'),
]
