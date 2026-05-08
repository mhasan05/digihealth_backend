from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, ActivityEvent
from .serializers import UserSerializer
from apps.patients.models import Patient
from core.utils import generate_health_id, validate_demographics


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get('identifier', '').strip()
        password = request.data.get('password', '')
        method = request.data.get('method', 'phone')

        if not identifier or not password:
            return Response({'detail': 'Identifier and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if method == 'health_id':
                user = User.objects.get(health_id=identifier)
            else:
                user = User.objects.get(phone=identifier)
        except User.DoesNotExist:
            return Response({'detail': 'ফোন নম্বর বা পাসওয়ার্ড সঠিক নয়'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({'detail': 'ফোন নম্বর বা পাসওয়ার্ড সঠিক নয়'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'detail': 'এই অ্যাকাউন্টটি নিষ্ক্রিয় করা হয়েছে'}, status=status.HTTP_403_FORBIDDEN)

        token = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token,
        })


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone', '').strip()
        password = request.data.get('password', '')
        name = request.data.get('name', '').strip()

        if not phone or not password or not name:
            return Response({'detail': 'Phone, password and name are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(phone=phone).exists():
            return Response({'detail': 'এই ফোন নম্বরে ইতোমধ্যে একটি অ্যাকাউন্ট আছে।'}, status=status.HTTP_400_BAD_REQUEST)

        demo, err = validate_demographics(request.data, require=True)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            health_id = generate_health_id()
            user = User.objects.create_user(
                phone=phone,
                password=password,
                name=name,
                health_id=health_id,
                roles=['patient'],
            )
            Patient.objects.create(
                user=user,
                age=demo['age'],
                gender=demo['gender'],
                blood_group=demo['blood_group'],
                address=demo['address'],
                subscription_tier='Free',
            )
            ActivityEvent.objects.create(
                type='patient_registered',
                description=f'New patient registered: {name} ({phone})',
            )

        token = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token,
        }, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # JWT is stateless; client should discard token
        return Response({'detail': 'Successfully logged out.'})


class DemoLoginView(APIView):
    permission_classes = [AllowAny]

    DEMO_PHONE_MAP = {
        'admin':       '01700000001',
        'owner':       '01711111111',
        'manager':     '01722000001',
        'pathologist': '01733000001',
        'patient':     '01799000001',
        'multiRole':   '01788000001',
    }

    def post(self, request):
        role = request.data.get('role', '')

        phone = self.DEMO_PHONE_MAP.get(role)
        if not phone:
            return Response({'detail': f'Unknown demo role: {role}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response(
                {'detail': f'Demo user for role "{role}" not found. Run seed_demo first.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        token = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token,
        })
