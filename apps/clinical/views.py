from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.permissions import IsManager
from core.utils import get_manager_profile, generate_health_id
from apps.accounts.models import User, ActivityEvent
from apps.patients.models import Patient
from apps.patients.serializers import PatientSerializer
from apps.staff.models import Doctor, HospitalDoctor, Nurse, Pathologist
from apps.staff.serializers import DoctorSerializer, HospitalDoctorPickSerializer, NurseSerializer
from .models import Bed, LabTest, Appointment, Admission, LabOrder, LabResult
from .serializers import (
    BedSerializer, AppointmentSerializer, AdmissionSerializer,
    LabOrderSerializer, LabResultSerializer
)


class ManagerDashboardView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.now().date()
        hospital = mgr.hospital
        hospital_apts = Appointment.objects.filter(hospital=hospital)

        data = {
            'todays_appointments': hospital_apts.filter(date=today).count(),
            'pending_confirmations': hospital_apts.filter(status='Pending').count(),
            'currently_admitted': Admission.objects.filter(
                appointment__hospital=hospital, discharged_at__isnull=True
            ).count(),
            'pending_lab_orders': LabOrder.objects.filter(hospital=hospital, status='Pending').count(),
        }
        return Response(data)


class AppointmentListView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        apts = Appointment.objects.filter(hospital=mgr.hospital).select_related(
            'patient__user', 'doctor', 'hospital'
        )
        return Response(AppointmentSerializer(apts, many=True).data)

    def post(self, request):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        patient_id = request.data.get('patient_id')
        doctor_id = request.data.get('doctor_id')
        date = request.data.get('date')
        time = request.data.get('time', '')
        reason = request.data.get('reason', '')
        status_val = request.data.get('status', 'Pending')

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient not found.'}, status=status.HTTP_404_NOT_FOUND)

        doctor = None
        if doctor_id:
            try:
                doctor = Doctor.objects.get(pk=doctor_id, hospital_attachments__hospital=mgr.hospital)
            except Doctor.DoesNotExist:
                return Response({'detail': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        apt = Appointment.objects.create(
            hospital=mgr.hospital,
            patient=patient,
            doctor=doctor,
            date=date,
            time=time,
            reason=reason,
            status=status_val,
        )
        return Response(AppointmentSerializer(apt).data, status=status.HTTP_201_CREATED)


class AppointmentDetailView(APIView):
    permission_classes = [IsManager]

    def get_appointment(self, pk, mgr):
        try:
            return Appointment.objects.select_related('patient__user', 'doctor').get(pk=pk, hospital=mgr.hospital)
        except Appointment.DoesNotExist:
            return None

    def put(self, request, pk):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        apt = self.get_appointment(pk, mgr)
        if not apt:
            return Response({'detail': 'Appointment not found.'}, status=status.HTTP_404_NOT_FOUND)

        if 'doctor_id' in request.data:
            doctor_id = request.data.get('doctor_id') or None
            if doctor_id:
                try:
                    apt.doctor = Doctor.objects.get(pk=doctor_id, hospital_attachments__hospital=mgr.hospital)
                except Doctor.DoesNotExist:
                    return Response({'detail': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)
            else:
                apt.doctor = None

        for field in ['date', 'time', 'reason', 'status']:
            if field in request.data:
                setattr(apt, field, request.data[field])
        apt.save()
        return Response(AppointmentSerializer(apt).data)

    def delete(self, request, pk):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        apt = self.get_appointment(pk, mgr)
        if not apt:
            return Response({'detail': 'Appointment not found.'}, status=status.HTTP_404_NOT_FOUND)
        apt.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AppointmentConfirmView(APIView):
    permission_classes = [IsManager]

    def post(self, request, pk):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            apt = Appointment.objects.select_related('patient__user', 'doctor').get(pk=pk, hospital=mgr.hospital)
        except Appointment.DoesNotExist:
            return Response({'detail': 'Appointment not found.'}, status=status.HTTP_404_NOT_FOUND)
        apt.status = 'Confirmed'
        apt.save()
        return Response(AppointmentSerializer(apt).data)


class AppointmentCancelView(APIView):
    permission_classes = [IsManager]

    def post(self, request, pk):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            apt = Appointment.objects.select_related('patient__user', 'doctor').get(pk=pk, hospital=mgr.hospital)
        except Appointment.DoesNotExist:
            return Response({'detail': 'Appointment not found.'}, status=status.HTTP_404_NOT_FOUND)
        apt.status = 'Cancelled'
        apt.save()
        return Response(AppointmentSerializer(apt).data)


class AppointmentAdmitView(APIView):
    permission_classes = [IsManager]

    def post(self, request, pk):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            apt = Appointment.objects.select_related('patient__user', 'doctor').get(pk=pk, hospital=mgr.hospital)
        except Appointment.DoesNotExist:
            return Response({'detail': 'Appointment not found.'}, status=status.HTTP_404_NOT_FOUND)

        if apt.admitted:
            return Response({'detail': 'Patient is already admitted.'}, status=status.HTTP_400_BAD_REQUEST)

        bed_id = request.data.get('bed_id')
        nurse_id = request.data.get('nurse_id') or None

        try:
            bed = Bed.objects.get(pk=bed_id, hospital=mgr.hospital, status='Available')
        except Bed.DoesNotExist:
            return Response({'detail': 'Bed not found or not available.'}, status=status.HTTP_404_NOT_FOUND)

        nurse = None
        if nurse_id:
            try:
                nurse = Nurse.objects.get(pk=nurse_id, hospital=mgr.hospital)
            except Nurse.DoesNotExist:
                return Response({'detail': 'Nurse not found.'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            admission = Admission.objects.create(
                appointment=apt,
                bed=bed,
                nurse=nurse,
                bed_price_snapshot=bed.price_per_day,
            )
            bed.status = 'Occupied'
            bed.save()
            apt.admitted = True
            apt.save()

        return Response(AdmissionSerializer(admission).data, status=status.HTTP_201_CREATED)


class AdmissionListView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        admissions = Admission.objects.filter(
            appointment__hospital=mgr.hospital
        ).select_related('appointment__patient__user', 'appointment__doctor', 'bed', 'nurse')
        return Response(AdmissionSerializer(admissions, many=True).data)

    def post(self, request):
        """Manually admit a patient — looks up by phone, creates user/patient if needed."""
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        phone = (request.data.get('phone') or '').strip()
        bed_id = request.data.get('bed_id')
        nurse_id = request.data.get('nurse_id') or None
        doctor_id = request.data.get('doctor_id') or None
        reason = (request.data.get('reason') or 'Direct admission').strip()

        if not phone:
            return Response({'detail': 'phone is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not bed_id:
            return Response({'detail': 'bed_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bed = Bed.objects.get(pk=bed_id, hospital=mgr.hospital, status='Available')
        except Bed.DoesNotExist:
            return Response({'detail': 'Bed not found or not available.'}, status=status.HTTP_404_NOT_FOUND)

        nurse = None
        if nurse_id:
            try:
                nurse = Nurse.objects.get(pk=nurse_id, hospital=mgr.hospital)
            except Nurse.DoesNotExist:
                return Response({'detail': 'Nurse not found.'}, status=status.HTTP_404_NOT_FOUND)

        doctor = None
        if doctor_id:
            try:
                doctor = Doctor.objects.get(pk=doctor_id, hospital_attachments__hospital=mgr.hospital)
            except Doctor.DoesNotExist:
                return Response({'detail': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            user = User.objects.filter(phone=phone).first()
            created_new_user = False

            if user is None:
                name = (request.data.get('name') or '').strip()
                if not name:
                    return Response(
                        {'detail': 'name is required for new patient registration.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                age = request.data.get('age', 0) or 0
                gender = request.data.get('gender', 'Other')
                blood_group = request.data.get('blood_group') or 'Unknown'

                health_id = generate_health_id()
                user = User.objects.create_user(
                    phone=phone,
                    password='123456',
                    name=name,
                    health_id=health_id,
                    roles=['patient'],
                )
                patient = Patient.objects.create(
                    user=user,
                    age=int(age) if age else 0,
                    gender=gender,
                    blood_group=blood_group,
                    address='',
                    subscription_tier='Free',
                )
                created_new_user = True
                ActivityEvent.objects.create(
                    type='patient_created',
                    description=f'Manual admission: registered new patient {name} ({phone})',
                )
            else:
                patient = Patient.objects.filter(user=user).first()
                if patient is None:
                    return Response(
                        {'detail': 'User exists but is not a patient.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            apt = Appointment.objects.create(
                hospital=mgr.hospital,
                patient=patient,
                doctor=doctor,
                date=timezone.now().date(),
                time=timezone.now().strftime('%H:%M'),
                reason=reason,
                status='Confirmed',
                admitted=True,
            )
            admission = Admission.objects.create(
                appointment=apt,
                bed=bed,
                nurse=nurse,
                bed_price_snapshot=bed.price_per_day,
            )
            bed.status = 'Occupied'
            bed.save()

            ActivityEvent.objects.create(
                type='patient_admitted',
                description=f'Manual admission: {patient.user.name} → bed {bed.number}',
            )

        data = AdmissionSerializer(admission).data
        data['created_new_user'] = created_new_user
        return Response(data, status=status.HTTP_201_CREATED)


class AdmissionDetailView(APIView):
    """Update an admission — change bed, change nurse, edit reason, or discharge."""
    permission_classes = [IsManager]

    def _get(self, mgr, pk):
        try:
            return Admission.objects.select_related(
                'appointment__hospital', 'appointment__patient__user',
                'appointment__doctor', 'bed', 'nurse',
            ).get(pk=pk, appointment__hospital=mgr.hospital)
        except Admission.DoesNotExist:
            return None

    def put(self, request, pk):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        admission = self._get(mgr, pk)
        if not admission:
            return Response({'detail': 'Admission not found.'}, status=status.HTTP_404_NOT_FOUND)
        if admission.discharged_at:
            return Response({'detail': 'Cannot edit a discharged admission.'}, status=status.HTTP_400_BAD_REQUEST)

        new_bed_id   = request.data.get('bed_id')
        new_nurse_id = request.data.get('nurse_id')
        new_doctor_id = request.data.get('doctor_id')
        # Sentinels so empty-string clears the field but absent key leaves it
        nurse_provided  = 'nurse_id' in request.data
        doctor_provided = 'doctor_id' in request.data
        reason          = request.data.get('reason')

        with transaction.atomic():
            # Bed transfer
            if new_bed_id and (not admission.bed or str(admission.bed_id) != str(new_bed_id)):
                try:
                    new_bed = Bed.objects.get(pk=new_bed_id, hospital=mgr.hospital, status='Available')
                except Bed.DoesNotExist:
                    return Response({'detail': 'New bed not available.'}, status=status.HTTP_400_BAD_REQUEST)
                if admission.bed:
                    admission.bed.status = 'Available'
                    admission.bed.save(update_fields=['status'])
                admission.bed = new_bed
                admission.bed_price_snapshot = new_bed.price_per_day
                new_bed.status = 'Occupied'
                new_bed.save(update_fields=['status'])

            # Nurse change (clearable)
            if nurse_provided:
                if new_nurse_id:
                    try:
                        admission.nurse = Nurse.objects.get(pk=new_nurse_id, hospital=mgr.hospital)
                    except Nurse.DoesNotExist:
                        return Response({'detail': 'Nurse not found.'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    admission.nurse = None

            admission.save()

            # Doctor + reason live on the linked appointment
            apt_dirty = False
            apt = admission.appointment
            if doctor_provided:
                if new_doctor_id:
                    try:
                        apt.doctor = Doctor.objects.get(pk=new_doctor_id, hospital_attachments__hospital=mgr.hospital)
                    except Doctor.DoesNotExist:
                        return Response({'detail': 'Doctor not found.'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    apt.doctor = None
                apt_dirty = True
            if reason is not None:
                apt.reason = (reason or '').strip()
                apt_dirty = True
            if apt_dirty:
                apt.save()

        return Response(AdmissionSerializer(admission).data)

    def delete(self, request, pk):
        """Discharge — sets discharged_at and frees the bed."""
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        admission = self._get(mgr, pk)
        if not admission:
            return Response({'detail': 'Admission not found.'}, status=status.HTTP_404_NOT_FOUND)
        if admission.discharged_at:
            return Response({'detail': 'Already discharged.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            admission.discharged_at = timezone.now()
            admission.save(update_fields=['discharged_at'])
            if admission.bed:
                admission.bed.status = 'Available'
                admission.bed.save(update_fields=['status'])

        return Response(AdmissionSerializer(admission).data)


class AvailableBedsView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        beds = Bed.objects.filter(hospital=mgr.hospital, status='Available')
        return Response(BedSerializer(beds, many=True).data)


class AvailableNursesView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        # Return every active nurse and annotate her current active-admission load
        # so managers can see workload while still being free to assign multiple patients.
        nurses = (
            Nurse.objects.filter(hospital=mgr.hospital, status='Active')
            .annotate(
                active_admission_count=Count(
                    'admissions',
                    filter=Q(admissions__discharged_at__isnull=True),
                )
            )
        )
        return Response(NurseSerializer(nurses, many=True).data)


class LabOrderListView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        orders = LabOrder.objects.filter(hospital=mgr.hospital).select_related(
            'patient__user', 'test', 'ordered_by_doctor', 'assigned_pathologist__user', 'hospital'
        )
        return Response(LabOrderSerializer(orders, many=True).data)

    def post(self, request):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        patient_id = request.data.get('patient_id')
        test_id = request.data.get('test_id')
        doctor_id = request.data.get('ordered_by_doctor_id') or None
        pathologist_id = request.data.get('assigned_pathologist_id') or None

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient not found.'}, status=status.HTTP_404_NOT_FOUND)

        from apps.clinical.models import LabTest as LabTestModel
        try:
            test = LabTestModel.objects.get(pk=test_id, hospital=mgr.hospital)
        except LabTestModel.DoesNotExist:
            return Response({'detail': 'Lab test not found.'}, status=status.HTTP_404_NOT_FOUND)

        doctor = None
        if doctor_id:
            try:
                doctor = Doctor.objects.get(pk=doctor_id, hospital_attachments__hospital=mgr.hospital)
            except Doctor.DoesNotExist:
                pass

        pathologist = None
        if pathologist_id:
            try:
                pathologist = Pathologist.objects.get(pk=pathologist_id, hospital=mgr.hospital)
            except Pathologist.DoesNotExist:
                return Response({'detail': 'Pathologist not found.'}, status=status.HTTP_404_NOT_FOUND)

        order = LabOrder.objects.create(
            hospital=mgr.hospital,
            patient=patient,
            test=test,
            ordered_by_doctor=doctor,
            assigned_pathologist=pathologist,
            status='Assigned' if pathologist else 'Pending',
        )
        return Response(LabOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class LabOrderAssignView(APIView):
    permission_classes = [IsManager]

    def post(self, request, pk):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            order = LabOrder.objects.get(pk=pk, hospital=mgr.hospital)
        except LabOrder.DoesNotExist:
            return Response({'detail': 'Lab order not found.'}, status=status.HTTP_404_NOT_FOUND)

        pathologist_id = request.data.get('pathologist_id')
        try:
            pathologist = Pathologist.objects.get(pk=pathologist_id, hospital=mgr.hospital)
        except Pathologist.DoesNotExist:
            return Response({'detail': 'Pathologist not found.'}, status=status.HTTP_404_NOT_FOUND)

        order.assigned_pathologist = pathologist
        order.status = 'Assigned'
        order.save()
        return Response(LabOrderSerializer(order).data)


class LabOrderCancelView(APIView):
    permission_classes = [IsManager]

    def post(self, request, pk):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            order = LabOrder.objects.get(pk=pk, hospital=mgr.hospital)
        except LabOrder.DoesNotExist:
            return Response({'detail': 'Lab order not found.'}, status=status.HTTP_404_NOT_FOUND)
        order.status = 'Cancelled'
        order.save()
        return Response(LabOrderSerializer(order).data)


class LabOrderResultView(APIView):
    permission_classes = [IsManager]

    def get(self, request, pk):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            order = LabOrder.objects.get(pk=pk, hospital=mgr.hospital)
        except LabOrder.DoesNotExist:
            return Response({'detail': 'Lab order not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            result = order.result
        except LabResult.DoesNotExist:
            return Response(None)
        return Response(LabResultSerializer(result).data)


class ManagerDoctorsView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        attachments = (
            HospitalDoctor.objects
            .filter(
                hospital=mgr.hospital,
                status='Active',
                doctor__availability_status='Available',
            )
            .select_related('doctor', 'hospital')
        )
        return Response(HospitalDoctorPickSerializer(attachments, many=True).data)


class ManagerLabTestsView(APIView):
    """Lab tests offered at the manager's hospital."""
    permission_classes = [IsManager]

    def get(self, request):
        from .serializers import LabTestSerializer
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        tests = LabTest.objects.filter(hospital=mgr.hospital, available=True).order_by('name')
        return Response(LabTestSerializer(tests, many=True).data)


class ManagerPathologistsView(APIView):
    """Active pathologists for the manager's hospital, with active-test counts."""
    permission_classes = [IsManager]

    def get(self, request):
        from django.db.models import Count, Q
        from apps.staff.serializers import PathologistSerializer
        mgr = get_manager_profile(request.user)
        if not mgr:
            return Response({'detail': 'Manager profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        paths = (
            Pathologist.objects
            .filter(hospital=mgr.hospital, status='Active')
            .select_related('user')
            .annotate(active_test_count=Count(
                'assigned_lab_orders',
                filter=Q(assigned_lab_orders__status='Assigned'),
            ))
        )
        data = PathologistSerializer(paths, many=True).data
        for row, p in zip(data, paths):
            row['active_test_count'] = p.active_test_count
        return Response(data)


class ManagerPatientsView(APIView):
    """Patient lookup for the manager portal.

    The frontend currently fetches everything and filters client-side, so we
    cap the response at 500 rows for now and support optional ?q= server-side
    filtering. TODO: move to a search-only endpoint with proper pagination once
    the manager UI is reworked.
    """
    permission_classes = [IsManager]

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        qs = Patient.objects.select_related('user').order_by('-created_at')
        if q:
            qs = qs.filter(
                Q(user__name__icontains=q)
                | Q(user__phone__icontains=q)
                | Q(user__health_id__icontains=q)
            )
        return Response(PatientSerializer(qs[:500], many=True).data)


class ManagerPatientDetailView(APIView):
    """Update a patient's demographics + their User name. Manager-only."""
    permission_classes = [IsManager]

    def put(self, request, pk):
        try:
            patient = Patient.objects.select_related('user').get(pk=pk)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient not found.'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            if 'name' in request.data:
                patient.user.name = (request.data.get('name') or '').strip() or patient.user.name
                patient.user.save(update_fields=['name'])
            for field in ['age', 'gender', 'blood_group', 'address']:
                if field in request.data:
                    val = request.data.get(field)
                    if field == 'age':
                        try:
                            val = int(val) if val not in (None, '') else patient.age
                        except (TypeError, ValueError):
                            val = patient.age
                    setattr(patient, field, val if val is not None else getattr(patient, field))
            patient.save()

        return Response(PatientSerializer(patient).data)


class WalkInPatientView(APIView):
    permission_classes = [IsManager]

    def post(self, request):
        name = request.data.get('name', '').strip()
        phone = request.data.get('phone', '').strip()
        age = request.data.get('age', 0)
        gender = request.data.get('gender', 'Other')
        blood_group = request.data.get('blood_group', 'Unknown')

        if not name or not phone:
            return Response({'detail': 'name and phone are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(phone=phone).exists():
            # Return existing patient
            try:
                user = User.objects.get(phone=phone)
                patient = Patient.objects.get(user=user)
                return Response(PatientSerializer(patient).data)
            except Patient.DoesNotExist:
                pass

        with transaction.atomic():
            health_id = generate_health_id()
            user = User.objects.create_user(
                phone=phone,
                password=health_id,  # Use health_id as initial password
                name=name,
                health_id=health_id,
                roles=['patient'],
            )
            patient = Patient.objects.create(
                user=user,
                age=age,
                gender=gender,
                blood_group=blood_group or 'Unknown',
                address='',
                subscription_tier='Free',
            )
            ActivityEvent.objects.create(
                type='patient_created',
                description=f'Walk-in patient registered: {name} ({phone})',
            )

        return Response(PatientSerializer(patient).data, status=status.HTTP_201_CREATED)
