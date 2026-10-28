from rest_framework import serializers
from .models import FieldStaff, FieldPrescription, FieldPrescriptionImage


class FieldStaffSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    prescription_count = serializers.SerializerMethodField()

    class Meta:
        model = FieldStaff
        fields = ['id', 'user_id', 'name', 'phone', 'area', 'status', 'prescription_count', 'created_at']

    def get_prescription_count(self, obj):
        return obj.prescriptions.count()


class FieldPrescriptionImageSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = FieldPrescriptionImage
        fields = ['id', 'page_no', 'file_url', 'size', 'content_type']

    def get_file_url(self, obj):
        """Short-lived signed URL — direct /media/ paths are not exposed."""
        from core.file_tokens import make_field_prescription_file_token
        token = make_field_prescription_file_token(obj.id)
        path = f'/api/files/field-prescriptions/?t={token}'
        request = self.context.get('request')
        return request.build_absolute_uri(path) if request else path


class FieldPrescriptionSerializer(serializers.ModelSerializer):
    """Shape shared by field staff, patients and doctors."""
    images = FieldPrescriptionImageSerializer(many=True, read_only=True)
    collected_by_name = serializers.CharField(source='collected_by.user.name', read_only=True, default='')

    class Meta:
        model = FieldPrescription
        fields = [
            'id', 'phone', 'patient_name', 'age', 'gender', 'notes',
            'status', 'collected_by_name', 'collected_at', 'claimed_at', 'images',
        ]


class AdminFieldPrescriptionSerializer(FieldPrescriptionSerializer):
    collected_by_id = serializers.UUIDField(source='collected_by.id', read_only=True, default=None)
    patient_id = serializers.UUIDField(source='patient.id', read_only=True, default=None)
    patient_account_name = serializers.CharField(source='patient.user.name', read_only=True, default='')

    class Meta(FieldPrescriptionSerializer.Meta):
        fields = FieldPrescriptionSerializer.Meta.fields + [
            'collected_by_id', 'patient_id', 'patient_account_name',
            'consent_given', 'dispute_reason',
        ]
