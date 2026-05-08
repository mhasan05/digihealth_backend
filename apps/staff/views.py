from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.permissions import IsOwner
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
from .models import Manager, Pathologist, Doctor, Nurse
from .serializers import ManagerSerializer, PathologistSerializer, DoctorSerializer, NurseSerializer


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
            'doctors_count': Doctor.objects.filter(hospital=hospital).count(),
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


# ─── Doctors ──────────────────────────────────────────────────────────────────

class DoctorListView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        doctors = Doctor.objects.filter(hospital=owner_profile.hospital)
        return Response(DoctorSerializer(doctors, many=True).data)

    def post(self, request):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get('name', '').strip()
        specialization = request.data.get('specialization', '')
        phone = request.data.get('phone', '').strip()
        schedule = request.data.get('schedule', '')
        status_val = request.data.get('status', 'Active')

        if not name or not phone:
            return Response({'detail': 'name and phone are required.'}, status=status.HTTP_400_BAD_REQUEST)

        doctor = Doctor.objects.create(
            hospital=owner_profile.hospital,
            name=name,
            specialization=specialization,
            phone=phone,
            schedule=schedule,
            status=status_val,
        )
        return Response(DoctorSerializer(doctor).data, status=status.HTTP_201_CREATED)


class DoctorDetailView(APIView):
    permission_classes = [IsOwner]

    def put(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            doctor = Doctor.objects.get(pk=pk, hospital=owner_profile.hospital)
        except Doctor.DoesNotExist:
            return Response({'detail': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        for field in ['name', 'specialization', 'phone', 'schedule', 'status']:
            if field in request.data:
                setattr(doctor, field, request.data[field])
        doctor.save()
        return Response(DoctorSerializer(doctor).data)

    def delete(self, request, pk):
        owner_profile = get_hospital_for_owner(request.user)
        if not owner_profile:
            return Response({'detail': 'Owner profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            doctor = Doctor.objects.get(pk=pk, hospital=owner_profile.hospital)
        except Doctor.DoesNotExist:
            return Response({'detail': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)
        doctor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
