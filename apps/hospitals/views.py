from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.permissions import IsAdmin
from core.utils import generate_health_id
from apps.accounts.models import User, ActivityEvent
from apps.accounts.serializers import ActivityEventSerializer
from .models import Hospital, Owner
from .serializers import HospitalSerializer, OwnerSerializer
from apps.staff.models import Manager, Pathologist
from apps.patients.models import Patient


class AdminDashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        recent_activity = ActivityEvent.objects.all()[:10]
        data = {
            'total_hospitals': Hospital.objects.count(),
            'total_owners': Owner.objects.count(),
            'total_managers': Manager.objects.count(),
            'total_patients': Patient.objects.count(),
            'recent_activity': ActivityEventSerializer(recent_activity, many=True).data,
        }
        return Response(data)


class HospitalListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        hospitals = Hospital.objects.all()
        return Response(HospitalSerializer(hospitals, many=True).data)

    def post(self, request):
        from core.utils import validate_demographics, ensure_patient_profile
        data = request.data

        # Extract owner data
        owner_name = data.get('owner_name', '').strip()
        owner_phone = data.get('owner_phone', '').strip()
        owner_email = data.get('owner_email', '').strip()
        owner_password = data.get('owner_password', 'demo1234')

        if not owner_name or not owner_phone:
            return Response({'detail': 'owner_name and owner_phone are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Demographics for the owner (age, gender, blood_group, address) — required
        owner_demo_input = {
            'age':         data.get('owner_age'),
            'gender':      data.get('owner_gender'),
            'blood_group': data.get('owner_blood_group'),
            'address':     data.get('owner_address'),
        }
        owner_demo, err = validate_demographics(owner_demo_input, require=True)
        if err:
            return Response({'detail': f'Owner {err}'}, status=status.HTTP_400_BAD_REQUEST)

        hospital_data = {
            k: v for k, v in data.items()
            if not k.startswith('owner_')
        }

        serializer = HospitalSerializer(data=hospital_data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            hospital = serializer.save()

            # Create owner user if doesn't exist
            if User.objects.filter(phone=owner_phone).exists():
                owner_user = User.objects.get(phone=owner_phone)
                if 'owner' not in owner_user.roles:
                    owner_user.roles = owner_user.roles + ['owner']
                    owner_user.save()
            else:
                health_id = generate_health_id()
                owner_user = User.objects.create_user(
                    phone=owner_phone,
                    password=owner_password,
                    name=owner_name,
                    email=owner_email or None,
                    health_id=health_id,
                    roles=['owner'],
                )

            ensure_patient_profile(owner_user, **owner_demo)

            Owner.objects.create(
                user=owner_user,
                hospital=hospital,
                is_primary=True,
                status='Active',
            )

            ActivityEvent.objects.create(
                type='hospital_created',
                description=f'Hospital created: {hospital.name_en}',
            )

        return Response(HospitalSerializer(hospital).data, status=status.HTTP_201_CREATED)


class HospitalDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return Hospital.objects.get(pk=pk)
        except Hospital.DoesNotExist:
            return None

    def get(self, request, pk):
        hospital = self.get_object(pk)
        if not hospital:
            return Response({'detail': 'Hospital not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(HospitalSerializer(hospital).data)

    def put(self, request, pk):
        hospital = self.get_object(pk)
        if not hospital:
            return Response({'detail': 'Hospital not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = HospitalSerializer(hospital, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        hospital = self.get_object(pk)
        if not hospital:
            return Response({'detail': 'Hospital not found.'}, status=status.HTTP_404_NOT_FOUND)
        if Hospital.objects.count() <= 1:
            return Response({'detail': 'শুধুমাত্র একটি হাসপাতাল থাকলে মুছে ফেলা যাবে না'}, status=status.HTTP_400_BAD_REQUEST)
        hospital.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HospitalToggleStatusView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            hospital = Hospital.objects.get(pk=pk)
        except Hospital.DoesNotExist:
            return Response({'detail': 'Hospital not found.'}, status=status.HTTP_404_NOT_FOUND)

        hospital.status = 'Paused' if hospital.status == 'Active' else 'Active'
        hospital.save()
        return Response(HospitalSerializer(hospital).data)
