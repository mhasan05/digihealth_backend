from django.urls import path
from .views import (
    DoctorMeView,
    DoctorPatientSearchView,
    DoctorPatientDetailView,
    DoctorPatientHivStatusView,
    DoctorPatientReportsView,
    DoctorPatientAccessLogView,
)

urlpatterns = [
    path('me/', DoctorMeView.as_view(), name='doctor-me'),
    path('patients/', DoctorPatientSearchView.as_view(), name='doctor-patient-search'),
    path('patients/<uuid:pk>/', DoctorPatientDetailView.as_view(), name='doctor-patient-detail'),
    path('patients/<uuid:pk>/hiv-status/', DoctorPatientHivStatusView.as_view(), name='doctor-patient-hiv-status'),
    path('patients/<uuid:pk>/reports/', DoctorPatientReportsView.as_view(), name='doctor-patient-reports'),
    path('patients/<uuid:pk>/access-log/', DoctorPatientAccessLogView.as_view(), name='doctor-patient-access-log'),
]
