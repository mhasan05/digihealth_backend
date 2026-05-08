from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
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
    """The 'user' portal — every authenticated user can view themselves as a patient.

    Multi-role users (manager / pathologist / owner / admin) can switch to the user
    portal without already having the 'patient' role. We grant the role and
    auto-create a Patient row on first hit so subsequent /api/patient/* calls work.
    """
    permission_classes = [IsAuthenticated]

    def _ensure_patient(self, user):
        roles = list(user.roles or [])
        if 'patient' not in roles:
            user.roles = roles + ['patient']
            user.save(update_fields=['roles'])
        patient = Patient.objects.select_related('user').filter(user=user).first()
        if not patient:
            patient = Patient.objects.create(
                user=user,
                age=0,
                gender='Other',
                blood_group='Unknown',
                address='',
                subscription_tier='Free',
            )
        return patient

    def get(self, request):
        patient = self._ensure_patient(request.user)
        return Response(PatientSerializer(patient).data)

    def put(self, request):
        """Self-edit: every authenticated user can update their own profile."""
        from core.utils import validate_demographics
        from django.db import transaction

        patient = self._ensure_patient(request.user)
        user = patient.user

        demo, err = validate_demographics(request.data, require=False)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if 'name' in request.data:
                name = (request.data.get('name') or '').strip()
                if name:
                    user.name = name
                    user.save(update_fields=['name'])
            if 'email' in request.data:
                user.email = (request.data.get('email') or '').strip() or None
                user.save(update_fields=['email'])

            # Demographics — partial update
            if demo:
                for k, v in demo.items():
                    setattr(patient, k, v)
                patient.save()
            # Address may be set to empty (allowed since we're updating self)
            if 'address' in request.data and 'address' not in demo:
                patient.address = (request.data.get('address') or '').strip()
                patient.save(update_fields=['address'])
            # Blood group can be cleared by sending empty string
            if 'blood_group' in request.data and 'blood_group' not in demo:
                patient.blood_group = 'Unknown'
                patient.save(update_fields=['blood_group'])

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
