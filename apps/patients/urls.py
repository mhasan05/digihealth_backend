from django.urls import path
from .views import (
    PathologistDashboardView,
    UpcomingTestsView,
    SubmitLabResultView,
    CompletedReportsView,
    PatientMeView,
    HealthMetricListView,
    HealthMetricDetailView,
    MedicalReportListView,
    MedicalReportDetailView,
    PrivacyLogView,
)

# NOTE: This file serves BOTH /api/pathologist/ and /api/patient/ routes
# The URL prefixes are handled in config/urls.py

# These are the pathologist routes - mounted at /api/pathologist/
pathologist_urlpatterns = [
    path('dashboard/', PathologistDashboardView.as_view(), name='pathologist-dashboard'),
    path('upcoming-tests/', UpcomingTestsView.as_view(), name='pathologist-upcoming-tests'),
    path('lab-orders/<uuid:pk>/submit-result/', SubmitLabResultView.as_view(), name='pathologist-submit-result'),
    path('completed-reports/', CompletedReportsView.as_view(), name='pathologist-completed-reports'),
]

# These are the patient routes - mounted at /api/patient/
patient_urlpatterns = [
    path('me/', PatientMeView.as_view(), name='patient-me'),
    path('metrics/', HealthMetricListView.as_view(), name='patient-metrics-list'),
    path('metrics/<uuid:pk>/', HealthMetricDetailView.as_view(), name='patient-metric-detail'),
    path('reports/', MedicalReportListView.as_view(), name='patient-reports-list'),
    path('reports/<uuid:pk>/', MedicalReportDetailView.as_view(), name='patient-report-detail'),
    path('privacy-log/', PrivacyLogView.as_view(), name='patient-privacy-log'),
]

urlpatterns = pathologist_urlpatterns
