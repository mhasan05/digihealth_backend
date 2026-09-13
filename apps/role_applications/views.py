from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import status

from core.permissions import IsAdmin
from core.file_tokens import read_role_application_file_token
from .models import RoleApplication
from .serializers import MyRoleApplicationSerializer, RoleApplicationSerializer

STAFF_ROLE_TYPES = ('nurse', 'medical_assistant', 'midwife')
ORG_REQUIRED_FIELDS = ['org_name', 'org_type', 'registration_number', 'validity_till', 'org_phone', 'upazilla', 'district', 'division']


class MyRoleApplicationListView(APIView):
    """Patient-facing: view my own applications, submit a new one."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        qs = RoleApplication.objects.filter(applicant=request.user)
        return Response(MyRoleApplicationSerializer(qs, many=True, context={'request': request}).data)

    def post(self, request):
        data = request.data
        role_type = (data.get('role_type') or '').strip()
        valid_types = dict(RoleApplication.ROLE_TYPE_CHOICES)
        if role_type not in valid_types:
            return Response(
                {'detail': f'role_type must be one of {list(valid_types)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if RoleApplication.objects.filter(applicant=request.user, role_type=role_type, status='Pending').exists():
            return Response(
                {'detail': 'You already have a pending application for this role.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fields = {'applicant': request.user, 'role_type': role_type}

        if role_type == 'organization_owner':
            missing = [f for f in ORG_REQUIRED_FIELDS if not (data.get(f) or '').strip()]
            if missing:
                return Response(
                    {'detail': f'Missing required fields: {", ".join(missing)}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            org_type = data.get('org_type').strip()
            if org_type not in dict(RoleApplication.ORG_TYPE_CHOICES):
                return Response(
                    {'detail': 'org_type must be one of Diagnostic/Clinic/Hospital.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            validity_till = parse_date(data.get('validity_till'))
            if not validity_till:
                return Response({'detail': 'validity_till must be a valid date (YYYY-MM-DD).'}, status=status.HTTP_400_BAD_REQUEST)
            if not data.get('document'):
                return Response({'detail': 'document (registration photo) is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not data.get('facility_photo'):
                return Response({'detail': 'facility_photo is required.'}, status=status.HTTP_400_BAD_REQUEST)

            fields.update({
                'org_name': data.get('org_name').strip(),
                'org_type': org_type,
                'registration_number': data.get('registration_number').strip(),
                'validity_till': validity_till,
                'org_phone': data.get('org_phone').strip(),
                'location_text': (data.get('location_text') or '').strip(),
                'upazilla': data.get('upazilla').strip(),
                'district': data.get('district').strip(),
                'division': data.get('division').strip(),
                'post_code': (data.get('post_code') or '').strip(),
                'document': data.get('document'),
                'facility_photo': data.get('facility_photo'),
            })
        else:
            registration_number = (data.get('registration_number') or '').strip()
            if not registration_number:
                return Response({'detail': 'registration_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not data.get('document'):
                return Response({'detail': 'document is required.'}, status=status.HTTP_400_BAD_REQUEST)
            fields['registration_number'] = registration_number
            fields['document'] = data.get('document')

        application = RoleApplication.objects.create(**fields)
        return Response(
            MyRoleApplicationSerializer(application, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class AdminRoleApplicationListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = RoleApplication.objects.select_related('applicant', 'reviewed_by').all()
        status_param = request.query_params.get('status')
        role_type_param = request.query_params.get('role_type')
        q = request.query_params.get('q', '').strip()
        if status_param:
            qs = qs.filter(status=status_param)
        if role_type_param:
            qs = qs.filter(role_type=role_type_param)
        if q:
            qs = qs.filter(
                Q(applicant__name__icontains=q)
                | Q(applicant__phone__icontains=q)
                | Q(registration_number__icontains=q)
                | Q(org_name__icontains=q)
            )
        return Response(RoleApplicationSerializer(qs, many=True, context={'request': request}).data)


class AdminRoleApplicationApproveView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            application = RoleApplication.objects.select_related('applicant').get(pk=pk)
        except RoleApplication.DoesNotExist:
            return Response({'detail': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)
        if application.status != 'Pending':
            return Response({'detail': 'Only pending applications can be approved.'}, status=status.HTTP_400_BAD_REQUEST)

        applicant = application.applicant

        with transaction.atomic():
            if application.role_type == 'doctor':
                from apps.staff.models import Doctor
                doctor = Doctor.objects.filter(user=applicant).first()
                if doctor:
                    doctor.name = applicant.name
                    doctor.phone = applicant.phone
                    doctor.bmdc_registration_no = application.registration_number or doctor.bmdc_registration_no
                    doctor.availability_status = 'Available'
                    doctor.save()
                else:
                    Doctor.objects.create(
                        user=applicant,
                        name=applicant.name,
                        phone=applicant.phone,
                        bmdc_registration_no=application.registration_number or None,
                        availability_status='Available',
                    )
                if 'doctor' not in applicant.roles:
                    applicant.roles = applicant.roles + ['doctor']
                    applicant.save(update_fields=['roles'])

            elif application.role_type in STAFF_ROLE_TYPES:
                from apps.staff.models import Nurse, MedicalAssistant, Midwife
                model = {'nurse': Nurse, 'medical_assistant': MedicalAssistant, 'midwife': Midwife}[application.role_type]
                model.objects.create(
                    user=applicant,
                    hospital=None,
                    name=applicant.name,
                    phone=applicant.phone,
                    status='Active',
                )

            elif application.role_type == 'organization_owner':
                from apps.hospitals.models import Hospital, Owner
                from apps.accounts.models import ActivityEvent

                address = ', '.join(p for p in [
                    application.location_text, application.upazilla,
                    application.district, application.division, application.post_code,
                ] if p)

                hospital = Hospital.objects.create(
                    name_bn=application.org_name,
                    name_en=application.org_name,
                    type=application.org_type,
                    status='Active',
                    address=address,
                    phone=application.org_phone,
                    email=applicant.email or '',
                    beds=0,
                    established=timezone.now().date(),
                )
                if 'owner' not in applicant.roles:
                    applicant.roles = applicant.roles + ['owner']
                    applicant.save(update_fields=['roles'])
                Owner.objects.create(user=applicant, hospital=hospital, is_primary=True, status='Active')
                ActivityEvent.objects.create(
                    type='hospital_created',
                    description=f'Hospital created via role application: {hospital.name_en}',
                )

            application.status = 'Approved'
            application.reviewed_by = request.user
            application.reviewed_at = timezone.now()
            application.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

        return Response(RoleApplicationSerializer(application, context={'request': request}).data)


class AdminRoleApplicationRejectView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            application = RoleApplication.objects.get(pk=pk)
        except RoleApplication.DoesNotExist:
            return Response({'detail': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)
        if application.status != 'Pending':
            return Response({'detail': 'Only pending applications can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)

        application.status = 'Rejected'
        application.rejection_reason = (request.data.get('reason') or '').strip()
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save(update_fields=['status', 'rejection_reason', 'reviewed_by', 'reviewed_at'])
        return Response(RoleApplicationSerializer(application, context={'request': request}).data)


class RoleApplicationFileView(APIView):
    """Serve a role-application document/facility_photo via a short-lived signed token."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        token = request.query_params.get('t') or ''
        result = read_role_application_file_token(token)
        if not result:
            raise Http404('Invalid or expired download link.')
        application_id, field = result
        try:
            application = RoleApplication.objects.get(pk=application_id)
        except (RoleApplication.DoesNotExist, ValueError):
            raise Http404('Application not found.')
        file_field = getattr(application, field)
        if not file_field:
            raise Http404('No file attached.')
        return FileResponse(file_field.open('rb'), as_attachment=False, filename=file_field.name.split('/')[-1])
