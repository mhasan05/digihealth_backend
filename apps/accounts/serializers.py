from rest_framework import serializers
from .models import User, ActivityEvent
from core.utils import get_active_hospital_id


class UserSerializer(serializers.ModelSerializer):
    active_hospital_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'phone', 'email', 'health_id', 'name', 'roles', 'active_hospital_id']

    def get_active_hospital_id(self, obj):
        return get_active_hospital_id(obj)


class ActivityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityEvent
        fields = ['id', 'type', 'description', 'timestamp']
