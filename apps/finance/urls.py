from django.urls import path
from apps.patients.views import (
    PatientMeView,
    HealthMetricListView,
    HealthMetricDetailView,
    MedicalReportListView,
    MedicalReportDetailView,
    PrivacyLogView,
)
from apps.role_applications.views import MyRoleApplicationListView
from apps.field_collection.views import PatientFieldPrescriptionListView, PatientFieldPrescriptionDisputeView

# These are the /api/patient/* routes
urlpatterns = [
    path('me/', PatientMeView.as_view(), name='patient-me'),
    path('metrics/', HealthMetricListView.as_view(), name='patient-metrics-list'),
    path('metrics/<uuid:pk>/', HealthMetricDetailView.as_view(), name='patient-metric-detail'),
    path('reports/', MedicalReportListView.as_view(), name='patient-reports-list'),
    path('reports/<uuid:pk>/', MedicalReportDetailView.as_view(), name='patient-report-detail'),
    path('privacy-log/', PrivacyLogView.as_view(), name='patient-privacy-log'),
    path('role-applications/', MyRoleApplicationListView.as_view(), name='patient-role-application-list'),
    path('field-prescriptions/', PatientFieldPrescriptionListView.as_view(), name='patient-field-prescription-list'),
    path('field-prescriptions/<uuid:pk>/dispute/', PatientFieldPrescriptionDisputeView.as_view(), name='patient-field-prescription-dispute'),
]
