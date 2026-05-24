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
            'blood_group', 'address', 'subscription_tier', 'health_id',
            'hiv_status', 'is_private', 'conditions', 'created_at',
        ]


class HealthMetricSerializer(serializers.ModelSerializer):
    patient_id = serializers.UUIDField(source='patient.id', read_only=True)

    class Meta:
        model = HealthMetric
        fields = ['id', 'patient_id', 'metric_type', 'date', 'value']


class MedicalReportSerializer(serializers.ModelSerializer):
    patient_id = serializers.UUIDField(source='patient.id', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = MedicalReport
        fields = ['id', 'patient_id', 'name', 'file_url', 'size', 'uploaded_at']

    def get_file_url(self, obj):
        """Short-lived signed URL — direct /media/ paths are not exposed."""
        if not obj.file:
            return ''
        from core.file_tokens import make_report_file_token
        token = make_report_file_token(obj.id)
        path = f'/api/files/reports/?t={token}'
        request = self.context.get('request')
        return request.build_absolute_uri(path) if request else path


class ReportAccessLogSerializer(serializers.ModelSerializer):
    patient_id = serializers.UUIDField(source='patient.id', read_only=True)
    report_id = serializers.SerializerMethodField()
    report_name = serializers.SerializerMethodField()
    accessor_name = serializers.CharField(source='accessor.name', read_only=True)

    class Meta:
        model = ReportAccessLog
        fields = ['id', 'patient_id', 'report_id', 'report_name', 'accessor_name', 'accessor_role', 'action', 'timestamp']

    def get_report_id(self, obj):
        return str(obj.report.id) if obj.report else None

    def get_report_name(self, obj):
        return obj.report.name if obj.report else ''
