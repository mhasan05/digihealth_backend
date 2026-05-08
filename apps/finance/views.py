# Finance views - patient endpoints are served from here
# The /api/patient/* routes are mounted via this app's urls.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.permissions import IsPatient
from apps.patients.models import Patient, HealthMetric, MedicalReport, ReportAccessLog
from apps.patients.serializers import (
    PatientSerializer, HealthMetricSerializer,
    MedicalReportSerializer, ReportAccessLogSerializer
)
from apps.patients.views import (
    PatientMeView, HealthMetricListView, HealthMetricDetailView,
    MedicalReportListView, MedicalReportDetailView, PrivacyLogView
)
