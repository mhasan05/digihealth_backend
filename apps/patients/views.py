from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import status
from django.http import FileResponse, Http404

from core.permissions import IsPatient, IsPathologist
from core.file_tokens import read_report_file_token
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
            # Privacy toggle — accepts true/false/1/0/"true"/"false".
            if 'is_private' in request.data:
                raw = request.data.get('is_private')
                if isinstance(raw, str):
                    raw = raw.strip().lower() in ('true', '1', 'yes', 'on')
                patient.is_private = bool(raw)
                patient.save(update_fields=['is_private'])
            # Self-reported chronic conditions — must be a list of allowed slugs.
            if 'conditions' in request.data:
                raw_list = request.data.get('conditions') or []
                if not isinstance(raw_list, list):
                    return Response(
                        {'detail': 'conditions must be a list.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                allowed = set(Patient.CONDITION_CHOICES)
                cleaned = []
                seen = set()
                for item in raw_list:
                    slug = str(item).strip().lower()
                    if slug in allowed and slug not in seen:
                        cleaned.append(slug)
                        seen.add(slug)
                patient.conditions = cleaned
                patient.save(update_fields=['conditions'])

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
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        reports = MedicalReport.objects.filter(patient=patient)
        return Response(MedicalReportSerializer(reports, many=True, context={'request': request}).data)

    def post(self, request):
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'detail': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)
        if uploaded.size > 10 * 1024 * 1024:
            return Response({'detail': 'File too large (max 10 MB).'}, status=status.HTTP_400_BAD_REQUEST)

        # Enforce 10-report FIFO limit
        existing = MedicalReport.objects.filter(patient=patient).order_by('uploaded_at')
        if existing.count() >= 10:
            existing.first().delete()

        report = MedicalReport.objects.create(
            patient=patient,
            name=request.data.get('name') or uploaded.name,
            file=uploaded,
            size=uploaded.size,
        )
        return Response(
            MedicalReportSerializer(report, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


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


class ReportFileView(APIView):
    """Serve a report file via a short-lived signed token. The token itself is
    the authorization — only people who got it via an auth-gated endpoint can
    use it. Direct /media/ paths are not exposed."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        token = request.query_params.get('t') or ''
        report_id = read_report_file_token(token)
        if not report_id:
            raise Http404('Invalid or expired download link.')
        try:
            report = MedicalReport.objects.get(pk=report_id)
        except (MedicalReport.DoesNotExist, ValueError):
            raise Http404('Report not found.')
        if not report.file:
            raise Http404('No file attached.')
        # Inline (as_attachment=False) so images and PDFs preview in the browser;
        # `<a download>` on the client still triggers a download via the filename hint.
        return FileResponse(report.file.open('rb'), as_attachment=False, filename=report.name)


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
