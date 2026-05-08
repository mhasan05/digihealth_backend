from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.permissions import IsPatient, IsPathologist
from apps.clinical.models import LabOrder, LabResult
from apps.clinical.serializers import LabOrderSerializer, LabResultSerializer
from .models import Patient, HealthMetric, MedicalReport, ReportAccessLog
from .serializers import (
    PatientSerializer, HealthMetricSerializer,
    MedicalReportSerializer, ReportAccessLogSerializer
)


# ─── Patient endpoints (/api/patient/*) ──────────────────────────────────────

class PatientMeView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        try:
            patient = Patient.objects.select_related('user').get(user=request.user)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PatientSerializer(patient).data)


class HealthMetricListView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        metrics = HealthMetric.objects.filter(patient=patient)
        return Response(HealthMetricSerializer(metrics, many=True).data)

    def post(self, request):
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        metric = HealthMetric.objects.create(
            patient=patient,
            metric_type=request.data.get('metric_type', ''),
            date=request.data.get('date'),
            value=request.data.get('value', ''),
        )
        return Response(HealthMetricSerializer(metric).data, status=status.HTTP_201_CREATED)


class HealthMetricDetailView(APIView):
    permission_classes = [IsPatient]

    def put(self, request, pk):
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            metric = HealthMetric.objects.get(pk=pk, patient=patient)
        except HealthMetric.DoesNotExist:
            return Response({'detail': 'Metric not found.'}, status=status.HTTP_404_NOT_FOUND)

        for field in ['metric_type', 'date', 'value']:
            if field in request.data:
                setattr(metric, field, request.data[field])
        metric.save()
        return Response(HealthMetricSerializer(metric).data)

    def delete(self, request, pk):
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            metric = HealthMetric.objects.get(pk=pk, patient=patient)
        except HealthMetric.DoesNotExist:
            return Response({'detail': 'Metric not found.'}, status=status.HTTP_404_NOT_FOUND)
        metric.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MedicalReportListView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        reports = MedicalReport.objects.filter(patient=patient)
        return Response(MedicalReportSerializer(reports, many=True).data)

    def post(self, request):
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Enforce 10 report limit
        existing = MedicalReport.objects.filter(patient=patient).order_by('uploaded_at')
        if existing.count() >= 10:
            oldest = existing.first()
            oldest.delete()

        report = MedicalReport.objects.create(
            patient=patient,
            name=request.data.get('name', ''),
            file_url=request.data.get('file_url', ''),
            size=request.data.get('size', 0),
        )
        return Response(MedicalReportSerializer(report).data, status=status.HTTP_201_CREATED)


class MedicalReportDetailView(APIView):
    permission_classes = [IsPatient]

    def delete(self, request, pk):
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            report = MedicalReport.objects.get(pk=pk, patient=patient)
        except MedicalReport.DoesNotExist:
            return Response({'detail': 'Report not found.'}, status=status.HTTP_404_NOT_FOUND)
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PrivacyLogView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        logs = ReportAccessLog.objects.filter(patient=patient).select_related('report', 'accessor')
        return Response(ReportAccessLogSerializer(logs, many=True).data)


# ─── Pathologist endpoints (/api/pathologist/*) ───────────────────────────────

class PathologistDashboardView(APIView):
    permission_classes = [IsPathologist]

    def get(self, request):
        from django.utils import timezone
        from apps.staff.models import Pathologist as PathologistProfile

        path_profile = PathologistProfile.objects.filter(user=request.user).first()
        if not path_profile:
            return Response({'detail': 'Pathologist profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.now().date()
        my_orders = LabOrder.objects.filter(assigned_pathologist=path_profile)
        assigned_pending = my_orders.filter(status='Assigned').count()
        total_assigned = my_orders.count()
        completed_today = LabResult.objects.filter(
            lab_order__assigned_pathologist=path_profile,
            submitted_at__date=today
        ).count()

        return Response({
            'assigned_pending': assigned_pending,
            'completed_today': completed_today,
            'total_assigned': total_assigned,
        })


class UpcomingTestsView(APIView):
    permission_classes = [IsPathologist]

    def get(self, request):
        from apps.staff.models import Pathologist as PathologistProfile
        path_profile = PathologistProfile.objects.filter(user=request.user).first()
        if not path_profile:
            return Response({'detail': 'Pathologist profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        orders = LabOrder.objects.filter(
            assigned_pathologist=path_profile, status='Assigned'
        ).select_related('patient__user', 'test', 'ordered_by_doctor', 'assigned_pathologist__user', 'hospital')
        return Response(LabOrderSerializer(orders, many=True).data)


class SubmitLabResultView(APIView):
    permission_classes = [IsPathologist]

    def post(self, request, pk):
        from apps.staff.models import Pathologist as PathologistProfile
        path_profile = PathologistProfile.objects.filter(user=request.user).first()
        if not path_profile:
            return Response({'detail': 'Pathologist profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            order = LabOrder.objects.get(pk=pk, assigned_pathologist=path_profile)
        except LabOrder.DoesNotExist:
            return Response({'detail': 'Lab order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(order, 'result'):
            return Response({'detail': 'Result already submitted.'}, status=status.HTTP_400_BAD_REQUEST)

        result = LabResult.objects.create(
            lab_order=order,
            findings=request.data.get('findings', ''),
            remarks=request.data.get('remarks', 'Normal'),
            submitted_by=request.user,
        )
        order.status = 'Completed'
        order.save()
        return Response(LabResultSerializer(result).data, status=status.HTTP_201_CREATED)


class CompletedReportsView(APIView):
    permission_classes = [IsPathologist]

    def get(self, request):
        from apps.staff.models import Pathologist as PathologistProfile
        path_profile = PathologistProfile.objects.filter(user=request.user).first()
        if not path_profile:
            return Response({'detail': 'Pathologist profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        orders = LabOrder.objects.filter(
            assigned_pathologist=path_profile, status='Completed'
        ).select_related('patient__user', 'test', 'ordered_by_doctor', 'assigned_pathologist__user', 'hospital')

        result_map = {r.lab_order_id: r for r in LabResult.objects.filter(lab_order__in=orders)}

        data = []
        for order in orders:
            order_data = LabOrderSerializer(order).data
            result = result_map.get(order.id)
            if result:
                order_data['result'] = LabResultSerializer(result).data
            data.append(order_data)

        return Response(data)
