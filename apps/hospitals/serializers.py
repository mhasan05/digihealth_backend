from rest_framework import serializers
from .models import Hospital, Owner


class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = [
            'id', 'name_bn', 'name_en', 'type', 'status',
            'address', 'phone', 'email', 'beds', 'established',
            'created_at', 'updated_at',
        ]


class OwnerSerializer(serializers.ModelSerializer):
    hospital_id = serializers.UUIDField(source='hospital.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    email = serializers.SerializerMethodField()

    class Meta:
        model = Owner
        fields = ['id', 'hospital_id', 'name', 'phone', 'email', 'is_primary', 'status', 'created_at']

    def get_email(self, obj):
        return obj.user.email or ''
