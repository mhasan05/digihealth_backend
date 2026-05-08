from rest_framework import serializers
from .models import Bed, LabTest, Appointment, Admission, LabOrder, LabResult


class BedSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)

    class Meta:
        model = Bed
        fields = ['id', 'hospital_id', 'number', 'ward', 'type', 'price_per_day', 'status', 'created_at']


class LabTestSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)

    class Meta:
        model = LabTest
        fields = ['id', 'hospital_id', 'name', 'price', 'duration', 'available', 'created_at']


class AppointmentSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)
    patient_id = serializers.UUIDField(source='patient.id', read_only=True)
    patient_name = serializers.CharField(source='patient.user.name', read_only=True)
    doctor_id = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'hospital_id', 'patient_id', 'patient_name',
            'doctor_id', 'doctor_name', 'date', 'time', 'reason',
            'status', 'admitted', 'created_at',
        ]

    def get_doctor_id(self, obj):
        return str(obj.doctor.id) if obj.doctor else None

    def get_doctor_name(self, obj):
        return obj.doctor.name if obj.doctor else ''


class AdmissionSerializer(serializers.ModelSerializer):
    appointment_id = serializers.UUIDField(source='appointment.id', read_only=True)
    patient_name = serializers.CharField(source='appointment.patient.user.name', read_only=True)
    bed_id = serializers.SerializerMethodField()
    bed_number = serializers.SerializerMethodField()
    ward = serializers.SerializerMethodField()
    nurse_id = serializers.SerializerMethodField()
    nurse_name = serializers.SerializerMethodField()

    class Meta:
        model = Admission
        fields = [
            'id', 'appointment_id', 'patient_name',
            'bed_id', 'bed_number', 'ward',
            'nurse_id', 'nurse_name',
            'admitted_at', 'discharged_at', 'bed_price_snapshot',
        ]

    def get_bed_id(self, obj):
        return str(obj.bed.id) if obj.bed else None

    def get_bed_number(self, obj):
        return obj.bed.number if obj.bed else ''

    def get_ward(self, obj):
        return obj.bed.ward if obj.bed else ''

    def get_nurse_id(self, obj):
        return str(obj.nurse.id) if obj.nurse else None

    def get_nurse_name(self, obj):
        return obj.nurse.name if obj.nurse else ''


class LabOrderSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)
    patient_id = serializers.UUIDField(source='patient.id', read_only=True)
    patient_name = serializers.CharField(source='patient.user.name', read_only=True)
    test_id = serializers.SerializerMethodField()
    test_name = serializers.SerializerMethodField()
    ordered_by_doctor_name = serializers.SerializerMethodField()
    assigned_pathologist_id = serializers.SerializerMethodField()
    assigned_pathologist_name = serializers.SerializerMethodField()

    class Meta:
        model = LabOrder
        fields = [
            'id', 'hospital_id', 'patient_id', 'patient_name',
            'test_id', 'test_name', 'ordered_by_doctor_name',
            'assigned_pathologist_id', 'assigned_pathologist_name',
            'status', 'created_at',
        ]

    def get_test_id(self, obj):
        return str(obj.test.id) if obj.test else None

    def get_test_name(self, obj):
        return obj.test.name if obj.test else ''

    def get_ordered_by_doctor_name(self, obj):
        return obj.ordered_by_doctor.name if obj.ordered_by_doctor else ''

    def get_assigned_pathologist_id(self, obj):
        return str(obj.assigned_pathologist.id) if obj.assigned_pathologist else None

    def get_assigned_pathologist_name(self, obj):
        return obj.assigned_pathologist.user.name if obj.assigned_pathologist else None


class LabResultSerializer(serializers.ModelSerializer):
    lab_order_id = serializers.UUIDField(source='lab_order.id', read_only=True)
    submitted_by_name = serializers.CharField(source='submitted_by.name', read_only=True)

    class Meta:
        model = LabResult
        fields = ['id', 'lab_order_id', 'findings', 'remarks', 'submitted_at', 'submitted_by_name']
