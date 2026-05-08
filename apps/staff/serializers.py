from rest_framework import serializers
from .models import Manager, Pathologist, Doctor, Nurse


class ManagerSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    email = serializers.SerializerMethodField()

    class Meta:
        model = Manager
        fields = ['id', 'hospital_id', 'name', 'phone', 'email', 'status', 'created_at']

    def get_email(self, obj):
        return obj.user.email or ''


class PathologistSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    email = serializers.SerializerMethodField()

    class Meta:
        model = Pathologist
        fields = ['id', 'hospital_id', 'name', 'phone', 'email', 'specialization', 'status', 'created_at']

    def get_email(self, obj):
        return obj.user.email or ''


class DoctorSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)

    class Meta:
        model = Doctor
        fields = ['id', 'hospital_id', 'name', 'specialization', 'phone', 'schedule', 'status', 'created_at']


class NurseSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)

    class Meta:
        model = Nurse
        fields = ['id', 'hospital_id', 'name', 'phone', 'ward', 'status', 'created_at']
