from rest_framework import serializers
from .models import Manager, Pathologist, Doctor, HospitalDoctor, Nurse


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
    """System-wide registry doctor. Used by the admin portal."""

    attached_hospital_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Doctor
        fields = [
            'id', 'name', 'phone', 'bmdc_registration_no', 'specialization',
            'availability_status', 'created_at', 'attached_hospital_count',
        ]


class HospitalDoctorSerializer(serializers.ModelSerializer):
    """Owner shape: row id = HospitalDoctor.id (so PUT/DELETE target the attachment)."""

    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)
    doctor_id = serializers.UUIDField(source='doctor.id', read_only=True)
    name = serializers.CharField(source='doctor.name', read_only=True)
    phone = serializers.CharField(source='doctor.phone', read_only=True)
    bmdc_registration_no = serializers.CharField(source='doctor.bmdc_registration_no', read_only=True)
    availability_status = serializers.CharField(source='doctor.availability_status', read_only=True)
    specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    created_at = serializers.DateTimeField(source='attached_at', read_only=True)

    class Meta:
        model = HospitalDoctor
        fields = [
            'id', 'hospital_id', 'doctor_id', 'name', 'phone', 'bmdc_registration_no',
            'specialization', 'availability_status', 'schedule', 'status', 'created_at',
        ]


class HospitalDoctorPickSerializer(serializers.ModelSerializer):
    """Manager shape: row id = Doctor.id (matches what gets stored on Appointment.doctor_id)."""

    id = serializers.UUIDField(source='doctor.id', read_only=True)
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)
    name = serializers.CharField(source='doctor.name', read_only=True)
    phone = serializers.CharField(source='doctor.phone', read_only=True)
    bmdc_registration_no = serializers.CharField(source='doctor.bmdc_registration_no', read_only=True)
    availability_status = serializers.CharField(source='doctor.availability_status', read_only=True)
    specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    created_at = serializers.DateTimeField(source='attached_at', read_only=True)

    class Meta:
        model = HospitalDoctor
        fields = [
            'id', 'hospital_id', 'name', 'phone', 'bmdc_registration_no',
            'specialization', 'availability_status', 'schedule', 'status', 'created_at',
        ]


class NurseSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)
    active_admission_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Nurse
        fields = ['id', 'hospital_id', 'name', 'phone', 'ward', 'status', 'created_at', 'active_admission_count']
