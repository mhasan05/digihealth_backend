from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.permissions import IsOwner, IsAdmin, IsDoctor
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from core.utils import (
    get_hospital_for_owner, generate_health_id,
    validate_demographics, ensure_patient_profile,
)
from apps.accounts.models import User, ActivityEvent
from apps.hospitals.models import Owner
from apps.hospitals.serializers import OwnerSerializer
from apps.clinical.models import Bed, LabTest
from apps.clinical.serializers import BedSerializer, LabTestSerializer
from apps.finance.models import MonthlyFinancial
from django.db.models import Q
from .models import Manager, Pathologist, Doctor, HospitalDoctor, Nurse
from .serializers import (
    ManagerSerializer, PathologistSerializer, DoctorSerializer,
    HospitalDoctorSerializer, NurseSerializer,
)


class OwnerDashboardView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        hospital = owner_profile.hospital
        hospital_id = hospital.id

        beds = Bed.objects.filter(hospital=hospital)
        beds_available = beds.filter(status='Available').count()
        beds_total = beds.count()

        financials = MonthlyFinancial.objects.filter(hospital=hospital).order_by('month')
        monthly_data = []
        BENGALI_MONTHS = ['জানু', 'ফেব্রু', 'মার্চ', 'এপ্রিল', 'মে', 'জুন', 'জুলাই', 'আগস্ট', 'সেপ্টে', 'অক্টো', 'নভে', 'ডিসে']

        for f in financials:
            try:
                month_num = int(f.month.split('-')[1]) - 1
                month_label = BENGALI_MONTHS[month_num]
            except (IndexError, ValueError):
                month_label = f.month
            monthly_data.append({
                'month': month_label,
                'revenue': float(f.revenue),
                'expenses': float(f.expenses),
                'profit': float(f.profit),
            })

        current_revenue = float(financials.last().revenue) if financials.exists() else 0
        current_expenses = float(financials.last().expenses) if financials.exists() else 0
        current_profit = current_revenue - current_expenses

        revenue_trend = 0
        profit_trend = 0
        if financials.count() >= 2:
            last = financials.last()
            prev = list(financials)[-2]
            if float(prev.revenue) != 0:
                revenue_trend = round(((float(last.revenue) - float(prev.revenue)) / float(prev.revenue)) * 100)
            prev_profit = float(prev.revenue) - float(prev.expenses)
            curr_profit = float(last.revenue) - float(last.expenses)
            if prev_profit != 0:
                profit_trend = round(((curr_profit - prev_profit) / abs(prev_profit)) * 100)

        data = {
            'managers_count': Manager.objects.filter(hospital=hospital).count(),
            'pathologists_count': Pathologist.objects.filter(hospital=hospital).count(),
            'doctors_count': HospitalDoctor.objects.filter(hospital=hospital).count(),
            'nurses_count': Nurse.objects.filter(hospital=hospital).count(),
            'beds_available': beds_available,
            'beds_total': beds_total,
            'active_tests': LabTest.objects.filter(hospital=hospital, available=True).count(),
            'current_revenue': current_revenue,
            'current_expenses': current_expenses,
            'current_profit': current_profit,
            'revenue_trend': revenue_trend,
            'profit_trend': profit_trend,
            'monthly_data': monthly_data,
        }
        return Response(data)


# ─── Co-owners ────────────────────────────────────────────────────────────────

class CoOwnerListView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        owners = Owner.objects.filter(hospital=owner_profile.hospital).select_related('user')
        return Response(OwnerSerializer(owners, many=True).data)

    def post(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get('name', '').strip()
        phone = request.data.get('phone', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', 'demo1234')

        if not name or not phone:
            return Response({'detail': 'name and phone are required.'}, status=status.HTTP_400_BAD_REQUEST)

        demo, err = validate_demographics(request.data, require=True)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if User.objects.filter(phone=phone).exists():
                co_owner_user = User.objects.get(phone=phone)
                if 'owner' not in co_owner_user.roles:
                    co_owner_user.roles = co_owner_user.roles + ['owner']
                    co_owner_user.save()
            else:
                health_id = generate_health_id()
                co_owner_user = User.objects.create_user(
                    phone=phone,
                    password=password,
                    name=name,
                    email=email or None,
                    health_id=health_id,
                    roles=['owner'],
                )

            ensure_patient_profile(co_owner_user, **demo)

            new_owner = Owner.objects.create(
                user=co_owner_user,
                hospital=owner_profile.hospital,
                is_primary=False,
                status='Active',
            )

        return Response(OwnerSerializer(new_owner).data, status=status.HTTP_201_CREATED)


class CoOwnerDetailView(APIView):
    permission_classes = [IsOwner]

    def delete(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            co_owner = Owner.objects.get(pk=pk, hospital=owner_profile.hospital)
        except Owner.DoesNotExist:
            return Response({'detail': 'Co-owner not found.'}, status=status.HTTP_404_NOT_FOUND)
        if co_owner.is_primary:
            return Response({'detail': 'Cannot remove primary owner.'}, status=status.HTTP_400_BAD_REQUEST)
        co_owner.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Managers ─────────────────────────────────────────────────────────────────

class ManagerListView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        managers = Manager.objects.filter(hospital=owner_profile.hospital).select_related('user')
        return Response(ManagerSerializer(managers, many=True).data)

    def post(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get('name', '').strip()
        phone = request.data.get('phone', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', 'demo1234')
        status_val = request.data.get('status', 'Active')

        if not name or not phone:
            return Response({'detail': 'name and phone are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(phone=phone).exists():
            return Response({'detail': 'A user with this phone already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        demo, err = validate_demographics(request.data, require=True)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            health_id = generate_health_id()
            user = User.objects.create_user(
                phone=phone,
                password=password,
                name=name,
                email=email or None,
                health_id=health_id,
                roles=['manager'],
            )
            ensure_patient_profile(user, **demo)
            manager = Manager.objects.create(
                user=user,
                hospital=owner_profile.hospital,
                status=status_val,
            )
            ActivityEvent.objects.create(
                type='manager_created',
                description=f'Manager added: {name} at {owner_profile.hospital.name_en}',
            )

        return Response(ManagerSerializer(manager).data, status=status.HTTP_201_CREATED)


class ManagerDetailView(APIView):
    permission_classes = [IsOwner]

    def put(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            manager = Manager.objects.select_related('user').get(pk=pk, hospital=owner_profile.hospital)
        except Manager.DoesNotExist:
            return Response({'detail': 'Manager not found.'}, status=status.HTTP_404_NOT_FOUND)

        if 'status' in request.data:
            manager.status = request.data['status']
            manager.save()
        if 'name' in request.data:
            manager.user.name = request.data['name']
            manager.user.save()
        if 'email' in request.data:
            manager.user.email = request.data['email']
            manager.user.save()

        # Demographics — optional on update; only provided fields are saved
        demo, err = validate_demographics(request.data, require=False)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        if demo:
            ensure_patient_profile(manager.user, **demo)

        return Response(ManagerSerializer(manager).data)

    def delete(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            manager = Manager.objects.get(pk=pk, hospital=owner_profile.hospital)
        except Manager.DoesNotExist:
            return Response({'detail': 'Manager not found.'}, status=status.HTTP_404_NOT_FOUND)
        manager.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Pathologists ─────────────────────────────────────────────────────────────

class PathologistListView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        pathologists = Pathologist.objects.filter(hospital=owner_profile.hospital).select_related('user')
        return Response(PathologistSerializer(pathologists, many=True).data)

    def post(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get('name', '').strip()
        phone = request.data.get('phone', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', 'demo1234')
        specialization = request.data.get('specialization', '')
        status_val = request.data.get('status', 'Active')

        if not name or not phone:
            return Response({'detail': 'name and phone are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(phone=phone).exists():
            return Response({'detail': 'A user with this phone already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        demo, err = validate_demographics(request.data, require=True)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            health_id = generate_health_id()
            user = User.objects.create_user(
                phone=phone,
                password=password,
                name=name,
                email=email or None,
                health_id=health_id,
                roles=['pathologist'],
            )
            ensure_patient_profile(user, **demo)
            pathologist = Pathologist.objects.create(
                user=user,
                hospital=owner_profile.hospital,
                specialization=specialization,
                status=status_val,
            )

        return Response(PathologistSerializer(pathologist).data, status=status.HTTP_201_CREATED)


class PathologistDetailView(APIView):
    permission_classes = [IsOwner]

    def put(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            pathologist = Pathologist.objects.select_related('user').get(pk=pk, hospital=owner_profile.hospital)
        except Pathologist.DoesNotExist:
            return Response({'detail': 'Pathologist not found.'}, status=status.HTTP_404_NOT_FOUND)

        if 'status' in request.data:
            pathologist.status = request.data['status']
        if 'specialization' in request.data:
            pathologist.specialization = request.data['specialization']
        pathologist.save()

        if 'name' in request.data:
            pathologist.user.name = request.data['name']
            pathologist.user.save()
        if 'email' in request.data:
            pathologist.user.email = request.data['email']
            pathologist.user.save()

        demo, err = validate_demographics(request.data, require=False)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        if demo:
            ensure_patient_profile(pathologist.user, **demo)

        return Response(PathologistSerializer(pathologist).data)

    def delete(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            pathologist = Pathologist.objects.get(pk=pk, hospital=owner_profile.hospital)
        except Pathologist.DoesNotExist:
            return Response({'detail': 'Pathologist not found.'}, status=status.HTTP_404_NOT_FOUND)
        pathologist.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Doctors (owner attaches from system-wide registry) ───────────────────────

class DoctorListView(APIView):
    """List doctors attached to the owner's hospital, or attach one from the registry."""
    permission_classes = [IsOwner]

    def get(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        attachments = HospitalDoctor.objects.filter(
            hospital=owner_profile.hospital,
        ).select_related('doctor', 'hospital')
        return Response(HospitalDoctorSerializer(attachments, many=True).data)

    def post(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        doctor_id = request.data.get('doctor_id')
        if not doctor_id:
            return Response({'detail': 'doctor_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            doctor = Doctor.objects.get(pk=doctor_id)
        except Doctor.DoesNotExist:
            return Response(
                {'detail': 'এই ডাক্তার সিস্টেম রেজিস্ট্রিতে নেই। প্রথমে অ্যাডমিনকে যোগ করতে বলুন।'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if doctor.availability_status == 'Unavailable':
            return Response(
                {'detail': 'এই ডাক্তার বর্তমানে অ্যাডমিন কর্তৃক অপ্রাপ্য চিহ্নিত। যুক্ত করা যাবে না।'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if HospitalDoctor.objects.filter(hospital=owner_profile.hospital, doctor=doctor).exists():
            return Response(
                {'detail': 'এই ডাক্তার ইতোমধ্যে আপনার হাসপাতালে যুক্ত আছে।'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        attachment = HospitalDoctor.objects.create(
            hospital=owner_profile.hospital,
            doctor=doctor,
            schedule=request.data.get('schedule', ''),
            status=request.data.get('status', 'Active'),
        )
        return Response(HospitalDoctorSerializer(attachment).data, status=status.HTTP_201_CREATED)


class DoctorDetailView(APIView):
    """Owner edits per-hospital fields (schedule + status only) or detaches.
    Activation is blocked while the global availability is Unavailable."""
    permission_classes = [IsOwner]

    def put(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            attachment = HospitalDoctor.objects.select_related('doctor').get(
                pk=pk, hospital=owner_profile.hospital,
            )
        except HospitalDoctor.DoesNotExist:
            return Response({'detail': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        unavailable = attachment.doctor.availability_status == 'Unavailable'

        if 'schedule' in request.data:
            attachment.schedule = request.data.get('schedule') or ''
        if 'status' in request.data:
            new_status = request.data.get('status')
            if new_status not in ('Active', 'Inactive'):
                return Response(
                    {'detail': "status must be 'Active' or 'Inactive'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if unavailable and new_status == 'Active':
                return Response(
                    {'detail': 'এই ডাক্তার অ্যাডমিন কর্তৃক অপ্রাপ্য — সক্রিয় করা যাবে না।'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            attachment.status = new_status

        attachment.save()
        return Response(HospitalDoctorSerializer(attachment).data)

    def delete(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            attachment = HospitalDoctor.objects.get(pk=pk, hospital=owner_profile.hospital)
        except HospitalDoctor.DoesNotExist:
            return Response({'detail': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)
        # Detach only — the doctor stays in the registry.
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DoctorRegistrySearchView(APIView):
    """Search the system-wide registry for AVAILABLE doctors not yet attached to this hospital."""
    permission_classes = [IsOwner]

    def get(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        q = (request.query_params.get('q') or '').strip()
        if not q:
            return Response([])

        already_attached = HospitalDoctor.objects.filter(
            hospital=owner_profile.hospital,
        ).values_list('doctor_id', flat=True)

        results = (
            Doctor.objects.filter(availability_status='Available')
            .exclude(id__in=already_attached)
            .filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(bmdc_registration_no__icontains=q))
            .order_by('name')[:20]
        )
        return Response(DoctorSerializer(results, many=True).data)


# ─── Nurses ───────────────────────────────────────────────────────────────────

class NurseListView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        nurses = Nurse.objects.filter(hospital=owner_profile.hospital)
        return Response(NurseSerializer(nurses, many=True).data)

    def post(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get('name', '').strip()
        phone = request.data.get('phone', '').strip()
        ward = request.data.get('ward', '')
        status_val = request.data.get('status', 'Active')

        if not name or not phone:
            return Response({'detail': 'name and phone are required.'}, status=status.HTTP_400_BAD_REQUEST)

        nurse = Nurse.objects.create(
            hospital=owner_profile.hospital,
            name=name,
            phone=phone,
            ward=ward,
            status=status_val,
        )
        return Response(NurseSerializer(nurse).data, status=status.HTTP_201_CREATED)


class NurseDetailView(APIView):
    permission_classes = [IsOwner]

    def put(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            nurse = Nurse.objects.get(pk=pk, hospital=owner_profile.hospital)
        except Nurse.DoesNotExist:
            return Response({'detail': 'Nurse not found.'}, status=status.HTTP_404_NOT_FOUND)

        for field in ['name', 'phone', 'ward', 'status']:
            if field in request.data:
                setattr(nurse, field, request.data[field])
        nurse.save()
        return Response(NurseSerializer(nurse).data)

    def delete(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            nurse = Nurse.objects.get(pk=pk, hospital=owner_profile.hospital)
        except Nurse.DoesNotExist:
            return Response({'detail': 'Nurse not found.'}, status=status.HTTP_404_NOT_FOUND)
        nurse.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Beds (Owner manages beds) ────────────────────────────────────────────────

class BedListView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        beds = Bed.objects.filter(hospital=owner_profile.hospital)
        return Response(BedSerializer(beds, many=True).data)

    def post(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        bed = Bed.objects.create(
            hospital=owner_profile.hospital,
            number=data.get('number', ''),
            ward=data.get('ward', ''),
            type=data.get('type', 'General'),
            price_per_day=data.get('price_per_day', 0),
            status=data.get('status', 'Available'),
        )
        return Response(BedSerializer(bed).data, status=status.HTTP_201_CREATED)


class BedDetailView(APIView):
    permission_classes = [IsOwner]

    def put(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            bed = Bed.objects.get(pk=pk, hospital=owner_profile.hospital)
        except Bed.DoesNotExist:
            return Response({'detail': 'Bed not found.'}, status=status.HTTP_404_NOT_FOUND)

        for field in ['number', 'ward', 'type', 'price_per_day', 'status']:
            if field in request.data:
                setattr(bed, field, request.data[field])
        bed.save()
        return Response(BedSerializer(bed).data)

    def delete(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            bed = Bed.objects.get(pk=pk, hospital=owner_profile.hospital)
        except Bed.DoesNotExist:
            return Response({'detail': 'Bed not found.'}, status=status.HTTP_404_NOT_FOUND)
        if bed.status == 'Occupied':
            return Response({'detail': 'দখলকৃত বেড মুছে ফেলা যাবে না'}, status=status.HTTP_400_BAD_REQUEST)
        bed.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Lab Tests (Owner manages lab tests) ──────────────────────────────────────

class LabTestListView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        tests = LabTest.objects.filter(hospital=owner_profile.hospital)
        return Response(LabTestSerializer(tests, many=True).data)

    def post(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        test = LabTest.objects.create(
            hospital=owner_profile.hospital,
            name=request.data.get('name', ''),
            price=request.data.get('price', 0),
            duration=request.data.get('duration', ''),
            available=request.data.get('available', True),
        )
        return Response(LabTestSerializer(test).data, status=status.HTTP_201_CREATED)


class LabTestDetailView(APIView):
    permission_classes = [IsOwner]

    def put(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            test = LabTest.objects.get(pk=pk, hospital=owner_profile.hospital)
        except LabTest.DoesNotExist:
            return Response({'detail': 'Lab test not found.'}, status=status.HTTP_404_NOT_FOUND)

        for field in ['name', 'price', 'duration', 'available']:
            if field in request.data:
                setattr(test, field, request.data[field])
        test.save()
        return Response(LabTestSerializer(test).data)

    def delete(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            test = LabTest.objects.get(pk=pk, hospital=owner_profile.hospital)
        except LabTest.DoesNotExist:
            return Response({'detail': 'Lab test not found.'}, status=status.HTTP_404_NOT_FOUND)
        test.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Admin: system-wide doctor registry ───────────────────────────────────────

class AdminDoctorListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        qs = Doctor.objects.annotate(attached_hospital_count=Count('hospital_attachments'))
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(phone__icontains=q) | Q(bmdc_registration_no__icontains=q)
            )
        return Response(DoctorSerializer(qs.order_by('name'), many=True).data)

    def post(self, request):
        from django.db import transaction
        from core.utils import generate_health_id

        name = (request.data.get('name') or '').strip()
        phone = (request.data.get('phone') or '').strip()
        bmdc = (request.data.get('bmdc_registration_no') or '').strip() or None
        specialization = (request.data.get('specialization') or '').strip()

        if not name or not phone:
            return Response({'detail': 'name and phone are required.'}, status=status.HTTP_400_BAD_REQUEST)
        if bmdc and Doctor.objects.filter(bmdc_registration_no=bmdc).exists():
            return Response(
                {'detail': 'এই BMDC রেজিস্ট্রেশন নম্বর ইতোমধ্যে আছে।'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create or reuse a User for the doctor's login. Default password '1234'
        # only applies to brand-new accounts — existing users keep their password.
        with transaction.atomic():
            user = User.objects.filter(phone=phone).first()
            if user is None:
                user = User.objects.create_user(
                    phone=phone,
                    password='1234',
                    name=name,
                    health_id=generate_health_id(),
                    roles=['doctor'],
                )
            else:
                if 'doctor' not in (user.roles or []):
                    user.roles = list(user.roles or []) + ['doctor']
                    user.save(update_fields=['roles'])
                if Doctor.objects.filter(user=user).exists():
                    return Response(
                        {'detail': 'এই ফোনে ইতোমধ্যে একটি ডাক্তার প্রোফাইল আছে।'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            doctor = Doctor.objects.create(
                user=user,
                name=name,
                phone=phone,
                bmdc_registration_no=bmdc,
                specialization=specialization,
            )
        return Response(DoctorSerializer(doctor).data, status=status.HTTP_201_CREATED)


class AdminDoctorDetailView(APIView):
    permission_classes = [IsAdmin]

    def put(self, request, pk):
        try:
            doctor = Doctor.objects.get(pk=pk)
        except Doctor.DoesNotExist:
            return Response({'detail': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        if 'name' in request.data:
            doctor.name = (request.data.get('name') or '').strip() or doctor.name
        if 'phone' in request.data:
            doctor.phone = (request.data.get('phone') or '').strip() or doctor.phone
        if 'bmdc_registration_no' in request.data:
            new_bmdc = (request.data.get('bmdc_registration_no') or '').strip() or None
            if new_bmdc and Doctor.objects.exclude(pk=doctor.pk).filter(bmdc_registration_no=new_bmdc).exists():
                return Response(
                    {'detail': 'এই BMDC রেজিস্ট্রেশন নম্বর অন্য ডাক্তারের সাথে যুক্ত।'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            doctor.bmdc_registration_no = new_bmdc
        if 'specialization' in request.data:
            doctor.specialization = (request.data.get('specialization') or '').strip()
        doctor.save()
        return Response(DoctorSerializer(doctor).data)

    def delete(self, request, pk):
        try:
            doctor = Doctor.objects.get(pk=pk)
        except Doctor.DoesNotExist:
            return Response({'detail': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)
        # Deletes the registry entry AND cascades all HospitalDoctor attachments.
        doctor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminDoctorAvailabilityView(APIView):
    """Toggle the global availability flag. Marking a doctor Unavailable also
    forces every existing hospital attachment to Inactive in one shot — that way
    owners and managers see a consistent state immediately."""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            doctor = Doctor.objects.get(pk=pk)
        except Doctor.DoesNotExist:
            return Response({'detail': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        new_status = (request.data.get('availability_status') or '').strip()
        if new_status not in ('Available', 'Unavailable'):
            return Response(
                {'detail': "availability_status must be 'Available' or 'Unavailable'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor.availability_status = new_status
        doctor.save(update_fields=['availability_status'])

        if new_status == 'Unavailable':
            HospitalDoctor.objects.filter(doctor=doctor, status='Active').update(status='Inactive')

        return Response(DoctorSerializer(doctor).data)


# ─── Doctor portal endpoints (/api/doctor/*) ──────────────────────────────────

class DoctorMeView(APIView):
    """Logged-in doctor's own profile + the hospitals they're attached to."""
    permission_classes = [IsDoctor]

    def get(self, request):
        doctor = Doctor.objects.filter(user=request.user).first()
        if not doctor:
            return Response({'detail': 'Doctor profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = DoctorSerializer(doctor).data
        data['hospitals'] = [
            {
                'id': str(att.hospital.id),
                'name': att.hospital.name_bn or att.hospital.name_en,
                'schedule': att.schedule,
                'status': att.status,
            }
            for att in HospitalDoctor.objects.filter(doctor=doctor).select_related('hospital')
        ]
        return Response(data)


class DoctorPatientSearchView(APIView):
    """System-wide patient search by phone, name or health_id.
    Patients with `is_private=True` are excluded so doctors can't find them.
    """
    permission_classes = [IsDoctor]

    def get(self, request):
        from apps.patients.models import Patient
        from apps.patients.serializers import PatientSerializer

        q = (request.query_params.get('q') or '').strip()
        if not q:
            return Response([])

        patients = (
            Patient.objects.select_related('user')
            .filter(is_private=False)
            .filter(
                Q(user__name__icontains=q)
                | Q(user__phone__icontains=q)
                | Q(user__health_id__icontains=q)
            )
            .order_by('user__name')[:30]
        )
        return Response(PatientSerializer(patients, many=True).data)


class DoctorPatientDetailView(APIView):
    """Full patient profile incl. HIV status. Private patients return 404."""
    permission_classes = [IsDoctor]

    def get(self, request, pk):
        from apps.patients.models import Patient
        from apps.patients.serializers import PatientSerializer
        try:
            patient = Patient.objects.select_related('user').get(pk=pk, is_private=False)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PatientSerializer(patient).data)


class DoctorPatientHivStatusView(APIView):
    """Doctor toggles a patient's HIV status (Negative ↔ Positive)."""
    permission_classes = [IsDoctor]

    def post(self, request, pk):
        from apps.patients.models import Patient
        from apps.patients.serializers import PatientSerializer

        try:
            patient = Patient.objects.get(pk=pk, is_private=False)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient not found.'}, status=status.HTTP_404_NOT_FOUND)

        new_status = (request.data.get('hiv_status') or '').strip()
        if new_status not in ('Negative', 'Positive'):
            return Response(
                {'detail': "hiv_status must be 'Negative' or 'Positive'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient.hiv_status = new_status
        patient.save(update_fields=['hiv_status'])
        return Response(PatientSerializer(patient).data)


class DoctorPatientReportsView(APIView):
    """List a patient's medical reports for the doctor to view/download.
    Private patients return 404 so reports stay hidden.
    """
    permission_classes = [IsDoctor]

    def get(self, request, pk):
        from apps.patients.models import Patient, MedicalReport
        from apps.patients.serializers import MedicalReportSerializer
        try:
            patient = Patient.objects.get(pk=pk, is_private=False)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient not found.'}, status=status.HTTP_404_NOT_FOUND)
        reports = MedicalReport.objects.filter(patient=patient)
        return Response(
            MedicalReportSerializer(reports, many=True, context={'request': request}).data,
        )


class DoctorPatientAccessLogView(APIView):
    """Record a privacy-log entry against a patient.

    Body: { "action": "searched" | "viewed" | "downloaded", "report_id"?: uuid }
    - 'searched' is a patient-level lookup; report_id is ignored.
    - 'viewed' / 'downloaded' require report_id and the report must belong to the patient.
    """
    permission_classes = [IsDoctor]

    def post(self, request, pk):
        from apps.patients.models import Patient, MedicalReport, ReportAccessLog

        try:
            patient = Patient.objects.get(pk=pk, is_private=False)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient not found.'}, status=status.HTTP_404_NOT_FOUND)

        action = (request.data.get('action') or '').strip()
        if action not in ('searched', 'viewed', 'downloaded'):
            return Response(
                {'detail': "action must be 'searched', 'viewed' or 'downloaded'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report = None
        if action in ('viewed', 'downloaded'):
            report_id = request.data.get('report_id')
            if not report_id:
                return Response(
                    {'detail': 'report_id is required for viewed/downloaded.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                report = MedicalReport.objects.get(pk=report_id, patient=patient)
            except MedicalReport.DoesNotExist:
                return Response({'detail': 'Report not found for this patient.'}, status=status.HTTP_404_NOT_FOUND)

        ReportAccessLog.objects.create(
            patient=patient,
            report=report,
            accessor=request.user,
            accessor_role='doctor',
            action=action,
        )
        return Response({'detail': 'logged'}, status=status.HTTP_201_CREATED)


# ─── Generic: change own password ─────────────────────────────────────────────

class ChangePasswordView(APIView):
    """Any authenticated user can change their own password."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current = (request.data.get('current_password') or '')
        new = (request.data.get('new_password') or '')

        if not current or not new:
            return Response(
                {'detail': 'current_password and new_password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new) < 4:
            return Response(
                {'detail': 'নতুন পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে।'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.check_password(current):
            return Response(
                {'detail': 'বর্তমান পাসওয়ার্ড সঠিক নয়।'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new)
        request.user.save(update_fields=['password'])
        return Response({'detail': 'পাসওয়ার্ড পরিবর্তন সফল হয়েছে।'})
