from rest_framework import serializers
from .models import Manager, Pathologist, Doctor, Nurse


def _patient_field(obj, field, default=None):
    """Pull a demographic value off the user's linked Patient row, if any."""
    p = getattr(obj.user, 'patient_profile', None)
    return getattr(p, field, default) if p else default


class ManagerSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    email = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    blood_group = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()

    class Meta:
        model = Manager
        fields = ['id', 'hospital_id', 'name', 'phone', 'email',
                  'age', 'gender', 'blood_group', 'address',
                  'status', 'created_at']

    def get_email(self, obj):       return obj.user.email or ''
    def get_age(self, obj):         return _patient_field(obj, 'age', 0)
    def get_gender(self, obj):      return _patient_field(obj, 'gender', '')
    def get_blood_group(self, obj): return _patient_field(obj, 'blood_group', '')
    def get_address(self, obj):     return _patient_field(obj, 'address', '')


class PathologistSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    email = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    blood_group = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()

    class Meta:
        model = Pathologist
        fields = ['id', 'hospital_id', 'name', 'phone', 'email', 'specialization',
                  'age', 'gender', 'blood_group', 'address',
                  'status', 'created_at']

    def get_email(self, obj):       return obj.user.email or ''
    def get_age(self, obj):         return _patient_field(obj, 'age', 0)
    def get_gender(self, obj):      return _patient_field(obj, 'gender', '')
    def get_blood_group(self, obj): return _patient_field(obj, 'blood_group', '')
    def get_address(self, obj):     return _patient_field(obj, 'address', '')


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
