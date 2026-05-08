from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.permissions import IsManager
from core.utils import get_manager_profile, generate_health_id
from apps.accounts.models import User, ActivityEvent
from apps.patients.models import Patient
from apps.patients.serializers import PatientSerializer
from apps.staff.models import Doctor, Nurse, Pathologist
from apps.staff.serializers import DoctorSerializer, NurseSerializer
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
                doctor = Doctor.objects.get(pk=doctor_id, hospital=mgr.hospital)
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
            try:
                apt.doctor = Doctor.objects.get(pk=request.data['doctor_id'], hospital=mgr.hospital)
            except Doctor.DoesNotExist:
                return Response({'detail': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

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
        nurse_id = request.data.get('nurse_id')

        try:
            bed = Bed.objects.get(pk=bed_id, hospital=mgr.hospital, status='Available')
        except Bed.DoesNotExist:
            return Response({'detail': 'Bed not found or not available.'}, status=status.HTTP_404_NOT_FOUND)

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
        ).select_related('appointment__patient__user', 'bed', 'nurse')
        return Response(AdmissionSerializer(admissions, many=True).data)


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
        nurses = Nurse.objects.filter(hospital=mgr.hospital, status='Active')
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
        doctor_id = request.data.get('ordered_by_doctor_id')

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
                doctor = Doctor.objects.get(pk=doctor_id, hospital=mgr.hospital)
            except Doctor.DoesNotExist:
                pass

        order = LabOrder.objects.create(
            hospital=mgr.hospital,
            patient=patient,
            test=test,
            ordered_by_doctor=doctor,
            status='Pending',
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
        doctors = Doctor.objects.filter(hospital=mgr.hospital, status='Active')
        return Response(DoctorSerializer(doctors, many=True).data)


class ManagerPatientsView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        patients = Patient.objects.select_related('user').all()
        return Response(PatientSerializer(patients, many=True).data)


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
