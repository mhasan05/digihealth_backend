from rest_framework import serializers
from .models import RoleApplication


class _RoleApplicationFileMixin:
    def _file_url(self, obj, field_name):
        f = getattr(obj, field_name)
        if not f:
            return ''
        from core.file_tokens import make_role_application_file_token
        token = make_role_application_file_token(obj.id, field_name)
        path = f'/api/files/role-applications/?t={token}'
        request = self.context.get('request')
        return request.build_absolute_uri(path) if request else path

    def get_document_url(self, obj):
        return self._file_url(obj, 'document')

    def get_facility_photo_url(self, obj):
        return self._file_url(obj, 'facility_photo')


class MyRoleApplicationSerializer(_RoleApplicationFileMixin, serializers.ModelSerializer):
    """Shape returned to the applicant themselves — no reviewer identity."""

    document_url = serializers.SerializerMethodField()
    facility_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = RoleApplication
        fields = [
            'id', 'role_type', 'status',
            'registration_number', 'document_url', 'facility_photo_url',
            'org_name', 'org_type', 'validity_till', 'org_phone',
            'location_text', 'upazilla', 'district', 'division', 'post_code',
            'rejection_reason', 'created_at', 'reviewed_at',
        ]


class RoleApplicationSerializer(_RoleApplicationFileMixin, serializers.ModelSerializer):
    """Full shape for admin review."""

    applicant_id = serializers.UUIDField(source='applicant.id', read_only=True)
    applicant_name = serializers.CharField(source='applicant.name', read_only=True)
    applicant_phone = serializers.CharField(source='applicant.phone', read_only=True)
    applicant_health_id = serializers.CharField(source='applicant.health_id', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.name', read_only=True, default='')
    document_url = serializers.SerializerMethodField()
    facility_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = RoleApplication
        fields = [
            'id', 'applicant_id', 'applicant_name', 'applicant_phone', 'applicant_health_id',
            'role_type', 'status',
            'registration_number', 'document_url', 'facility_photo_url',
            'org_name', 'org_type', 'validity_till', 'org_phone',
            'location_text', 'upazilla', 'district', 'division', 'post_code',
            'reviewed_by_name', 'reviewed_at', 'rejection_reason', 'created_at',
        ]
