from rest_framework import serializers
from .models import User, ActivityEvent
from core.utils import get_active_hospital_id
from core.consent import needs_consent


class UserSerializer(serializers.ModelSerializer):
    active_hospital_id = serializers.SerializerMethodField()
    # True when the web app must show the privacy notice before the portal.
    consent_required = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'phone', 'email', 'health_id', 'name', 'roles', 'active_hospital_id', 'consent_required']

    def get_active_hospital_id(self, obj):
        return get_active_hospital_id(obj)

    def get_consent_required(self, obj):
        return needs_consent(obj)


class ActivityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityEvent
        fields = ['id', 'type', 'description', 'timestamp']
