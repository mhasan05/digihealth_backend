from rest_framework import serializers
from .models import Patient, HealthMetric, MedicalReport, ReportAccessLog


class PatientSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    health_id = serializers.CharField(source='user.health_id', read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'user_id', 'name', 'phone', 'age', 'gender',
            'blood_group', 'address', 'subscription_tier', 'health_id', 'created_at',
        ]


class HealthMetricSerializer(serializers.ModelSerializer):
    patient_id = serializers.UUIDField(source='patient.id', read_only=True)

    class Meta:
        model = HealthMetric
        fields = ['id', 'patient_id', 'metric_type', 'date', 'value']


class MedicalReportSerializer(serializers.ModelSerializer):
    patient_id = serializers.UUIDField(source='patient.id', read_only=True)

    class Meta:
        model = MedicalReport
        fields = ['id', 'patient_id', 'name', 'file_url', 'size', 'uploaded_at']


class ReportAccessLogSerializer(serializers.ModelSerializer):
    patient_id = serializers.UUIDField(source='patient.id', read_only=True)
    report_id = serializers.UUIDField(source='report.id', read_only=True)
    report_name = serializers.CharField(source='report.name', read_only=True)
    accessor_name = serializers.CharField(source='accessor.name', read_only=True)

    class Meta:
        model = ReportAccessLog
        fields = ['id', 'patient_id', 'report_id', 'report_name', 'accessor_name', 'accessor_role', 'action', 'timestamp']
