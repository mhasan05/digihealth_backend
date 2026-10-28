import uuid

from django.db import transaction
from django.http import FileResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import status

from core.permissions import IsAdmin, IsDoctor, IsFieldStaff, IsPatient
from core.file_tokens import read_field_prescription_file_token
from core.utils import normalize_bd_phone, generate_health_id
from apps.accounts.models import User, ActivityEvent
from .models import FieldStaff, FieldPrescription, FieldPrescriptionImage
from .serializers import (
    FieldStaffSerializer, FieldPrescriptionSerializer, AdminFieldPrescriptionSerializer,
)
from .services import link_field_prescriptions


MAX_IMAGES_PER_PRESCRIPTION = 10
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = ('image/jpeg', 'image/png', 'image/webp', 'application/pdf')

INVALID_PHONE_MSG = 'Enter a valid Bangladeshi mobile number (01XXXXXXXXX).'


def _with_images(qs):
    return qs.select_related('collected_by__user', 'patient__user').prefetch_related('images')


def _mask_name(name):
    return ' '.join(part[0] + '*' * (len(part) - 1) for part in (name or '').split())


# ─── Admin: field staff management (/api/admin/field-staff/*) ────────────────

class AdminFieldStaffListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        staff = FieldStaff.objects.select_related('user')
        return Response(FieldStaffSerializer(staff, many=True).data)

    def post(self, request):
        name = request.data.get('name', '').strip()
        phone = normalize_bd_phone(request.data.get('phone'))
        password = request.data.get('password', '')
        area = request.data.get('area', '').strip()

        if not name or not password:
            return Response({'detail': 'name, phone and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not phone:
            return Response({'detail': INVALID_PHONE_MSG}, status=status.HTTP_400_BAD_REQUEST)
        if len(password) < 6:
            return Response({'detail': 'Password must be at least 6 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(phone=phone).exists():
            return Response({'detail': 'A user with this phone already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = User.objects.create_user(
                phone=phone,
                password=password,
                name=name,
                health_id=generate_health_id(),
                roles=['field_staff'],
            )
            staff = FieldStaff.objects.create(user=user, area=area, created_by=request.user)
            ActivityEvent.objects.create(
                type='field_staff_created',
                description=f'Field staff added: {name} ({phone})',
            )

        return Response(FieldStaffSerializer(staff).data, status=status.HTTP_201_CREATED)


class AdminFieldStaffDetailView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            staff = FieldStaff.objects.select_related('user').get(pk=pk)
        except FieldStaff.DoesNotExist:
            return Response({'detail': 'Field staff not found.'}, status=status.HTTP_404_NOT_FOUND)
        user = staff.user

        if 'status' in request.data:
            status_val = request.data['status']
            if status_val not in ('Active', 'Inactive'):
                return Response({'detail': "status must be 'Active' or 'Inactive'."}, status=status.HTTP_400_BAD_REQUEST)
            staff.status = status_val
            # Inactive staff are blocked at login too, not just at upload.
            user.is_active = status_val == 'Active'
        if 'area' in request.data:
            staff.area = (request.data['area'] or '').strip()
        if 'name' in request.data:
            name = (request.data['name'] or '').strip()
            if not name:
                return Response({'detail': 'name cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)
            user.name = name
        if request.data.get('password'):
            if len(request.data['password']) < 6:
                return Response({'detail': 'Password must be at least 6 characters.'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(request.data['password'])

        with transaction.atomic():
            user.save()
            staff.save()
        return Response(FieldStaffSerializer(staff).data)


# ─── Admin: all field prescriptions (/api/admin/field-prescriptions/*) ───────

class AdminFieldPrescriptionListView(APIView):
    """Filters: status, phone, staff (FieldStaff id), date_from, date_to (YYYY-MM-DD)."""
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = _with_images(FieldPrescription.objects.all())
        params = request.query_params
        if params.get('status'):
            qs = qs.filter(status=params['status'])
        if params.get('phone'):
            qs = qs.filter(phone__contains=normalize_bd_phone(params['phone']) or params['phone'].strip())
        if params.get('staff'):
            qs = qs.filter(collected_by_id=params['staff'])
        if params.get('date_from'):
            qs = qs.filter(collected_at__date__gte=params['date_from'])
        if params.get('date_to'):
            qs = qs.filter(collected_at__date__lte=params['date_to'])
        return Response(AdminFieldPrescriptionSerializer(qs, many=True, context={'request': request}).data)


class AdminFieldPrescriptionDetailView(APIView):
    """Resolve disputes: correct a mistyped `phone` and/or set `status` back to
    'unclaimed'. Either one unlinks the prescription and re-links it to the
    account on its (possibly new) phone, if there is one."""
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            rx = FieldPrescription.objects.get(pk=pk)
        except FieldPrescription.DoesNotExist:
            return Response({'detail': 'Prescription not found.'}, status=status.HTTP_404_NOT_FOUND)

        relink = False
        if 'phone' in request.data:
            phone = normalize_bd_phone(request.data['phone'])
            if not phone:
                return Response({'detail': INVALID_PHONE_MSG}, status=status.HTTP_400_BAD_REQUEST)
            relink = relink or phone != rx.phone
            rx.phone = phone
        if 'status' in request.data:
            if request.data['status'] != 'unclaimed':
                return Response({'detail': "status can only be set to 'unclaimed'."}, status=status.HTTP_400_BAD_REQUEST)
            relink = True

        if relink:
            with transaction.atomic():
                rx.patient = None
                rx.status = 'unclaimed'
                rx.claimed_at = None
                rx.dispute_reason = ''
                rx.save()
                owner = User.objects.filter(phone=rx.phone).first()
                if owner:
                    link_field_prescriptions(owner)
            rx.refresh_from_db()

        rx = _with_images(FieldPrescription.objects.filter(pk=rx.pk)).get()
        return Response(AdminFieldPrescriptionSerializer(rx, context={'request': request}).data)


# ─── Field staff app (/api/field/*) ───────────────────────────────────────────

def _active_field_staff(user):
    return FieldStaff.objects.filter(user=user, status='Active').first()


class FieldMeView(APIView):
    permission_classes = [IsFieldStaff]

    def get(self, request):
        staff = _active_field_staff(request.user)
        if not staff:
            return Response({'detail': 'Field staff profile not found or inactive.'}, status=status.HTTP_403_FORBIDDEN)
        return Response(FieldStaffSerializer(staff).data)


class FieldPhoneLookupView(APIView):
    """Tell field staff whether a number has an account, with a masked name so
    they can confirm with the patient. Never returns any prescription data."""
    permission_classes = [IsFieldStaff]

    def get(self, request):
        phone = normalize_bd_phone(request.query_params.get('phone'))
        if not phone:
            return Response({'detail': INVALID_PHONE_MSG}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(phone=phone).first()
        if user and 'patient' not in user.roles:
            user = None
        return Response({
            'phone': phone,
            'registered': user is not None,
            'masked_name': _mask_name(user.name) if user else '',
        })


class FieldPrescriptionListView(APIView):
    """GET: the staff member's own uploads.
    POST (multipart): phone, consent_given=true, images (1–10 files), optional
    patient_name, age, gender, notes, client_id (UUID, makes retries safe)."""
    permission_classes = [IsFieldStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        staff = _active_field_staff(request.user)
        if not staff:
            return Response({'detail': 'Field staff profile not found or inactive.'}, status=status.HTTP_403_FORBIDDEN)
        qs = _with_images(FieldPrescription.objects.filter(collected_by=staff))
        return Response(FieldPrescriptionSerializer(qs, many=True, context={'request': request}).data)

    def post(self, request):
        staff = _active_field_staff(request.user)
        if not staff:
            return Response({'detail': 'Field staff profile not found or inactive.'}, status=status.HTTP_403_FORBIDDEN)

        client_id = None
        if request.data.get('client_id'):
            try:
                client_id = uuid.UUID(str(request.data['client_id']))
            except ValueError:
                return Response({'detail': 'client_id must be a UUID.'}, status=status.HTTP_400_BAD_REQUEST)
            existing = FieldPrescription.objects.filter(client_id=client_id).first()
            if existing:
                if existing.collected_by_id != staff.id:
                    return Response({'detail': 'client_id already used.'}, status=status.HTTP_400_BAD_REQUEST)
                existing = _with_images(FieldPrescription.objects.filter(pk=existing.pk)).get()
                return Response(FieldPrescriptionSerializer(existing, context={'request': request}).data)

        phone = normalize_bd_phone(request.data.get('phone'))
        if not phone:
            return Response({'detail': INVALID_PHONE_MSG}, status=status.HTTP_400_BAD_REQUEST)
        if str(request.data.get('consent_given', '')).lower() not in ('true', '1'):
            return Response({'detail': "The patient's consent is required."}, status=status.HTTP_400_BAD_REQUEST)

        images = request.FILES.getlist('images')
        if not images:
            return Response({'detail': 'At least one prescription image is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(images) > MAX_IMAGES_PER_PRESCRIPTION:
            return Response({'detail': f'At most {MAX_IMAGES_PER_PRESCRIPTION} pages per prescription.'}, status=status.HTTP_400_BAD_REQUEST)
        for f in images:
            if f.size > MAX_IMAGE_BYTES:
                return Response({'detail': f'{f.name} is too large (max 10 MB).'}, status=status.HTTP_400_BAD_REQUEST)
            if f.content_type not in ALLOWED_CONTENT_TYPES:
                return Response({'detail': f'{f.name}: only JPEG, PNG, WebP or PDF files are allowed.'}, status=status.HTTP_400_BAD_REQUEST)

        age = request.data.get('age')
        if age in (None, ''):
            age = None
        else:
            try:
                age = int(age)
            except (TypeError, ValueError):
                return Response({'detail': 'age must be a number.'}, status=status.HTTP_400_BAD_REQUEST)
            if age < 0 or age > 150:
                return Response({'detail': 'age must be between 0 and 150.'}, status=status.HTTP_400_BAD_REQUEST)
        gender = (request.data.get('gender') or '').strip()
        if gender and gender not in ('Male', 'Female', 'Other'):
            return Response({'detail': "gender must be 'Male', 'Female' or 'Other'."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            rx = FieldPrescription.objects.create(
                phone=phone,
                patient_name=(request.data.get('patient_name') or '').strip(),
                age=age,
                gender=gender,
                notes=(request.data.get('notes') or '').strip(),
                consent_given=True,
                collected_by=staff,
                client_id=client_id,
            )
            for page_no, f in enumerate(images, start=1):
                FieldPrescriptionImage.objects.create(
                    prescription=rx, file=f, page_no=page_no,
                    size=f.size, content_type=f.content_type,
                )
            # A number that already has an account is linked straight away.
            owner = User.objects.filter(phone=phone).first()
            if owner:
                link_field_prescriptions(owner)

        rx = _with_images(FieldPrescription.objects.filter(pk=rx.pk)).get()
        return Response(
            FieldPrescriptionSerializer(rx, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


# ─── Patient (/api/patient/field-prescriptions/*) ─────────────────────────────

class PatientFieldPrescriptionListView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        qs = _with_images(FieldPrescription.objects.filter(
            patient__user=request.user, status='claimed',
        ))
        return Response(FieldPrescriptionSerializer(qs, many=True, context={'request': request}).data)


class PatientFieldPrescriptionDisputeView(APIView):
    """"Not mine": unlinks the prescription and sends it to the admin queue."""
    permission_classes = [IsPatient]
    parser_classes = [JSONParser, FormParser]

    def post(self, request, pk):
        try:
            rx = FieldPrescription.objects.get(pk=pk, patient__user=request.user, status='claimed')
        except FieldPrescription.DoesNotExist:
            return Response({'detail': 'Prescription not found.'}, status=status.HTTP_404_NOT_FOUND)
        rx.status = 'disputed'
        rx.patient = None
        rx.claimed_at = None
        rx.dispute_reason = (request.data.get('reason') or '').strip()
        rx.save()
        ActivityEvent.objects.create(
            type='field_prescription_disputed',
            description=f'Field prescription {rx.id} reported as not theirs by {request.user.phone}',
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Doctor (/api/doctor/patients/<pk>/field-prescriptions/) ──────────────────

class DoctorPatientFieldPrescriptionsView(APIView):
    """Field prescriptions of a registered patient. Only linked ones exist here:
    a prescription for a number without an account is invisible to doctors.
    Private patients return 404, like the other doctor patient endpoints."""
    permission_classes = [IsDoctor]

    def get(self, request, pk):
        from apps.patients.models import Patient, ReportAccessLog
        try:
            patient = Patient.objects.get(pk=pk, is_private=False)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient not found.'}, status=status.HTTP_404_NOT_FOUND)
        qs = _with_images(FieldPrescription.objects.filter(patient=patient, status='claimed'))
        if qs:
            ReportAccessLog.objects.create(
                patient=patient, accessor=request.user, accessor_role='doctor', action='viewed',
            )
        return Response(FieldPrescriptionSerializer(qs, many=True, context={'request': request}).data)


# ─── Signed file delivery (/api/files/field-prescriptions/) ───────────────────

class FieldPrescriptionFileView(APIView):
    """Serve a prescription image via a short-lived signed token. The token is
    the authorization; it is only handed out by the auth-gated endpoints above."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        image_id = read_field_prescription_file_token(request.query_params.get('t') or '')
        if not image_id:
            raise Http404('Invalid or expired link.')
        try:
            image = FieldPrescriptionImage.objects.get(pk=image_id)
        except (FieldPrescriptionImage.DoesNotExist, ValueError):
            raise Http404('Image not found.')
        return FileResponse(image.file.open('rb'), as_attachment=False, content_type=image.content_type or None)
