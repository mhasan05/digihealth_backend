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
    age = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    blood_group = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()

    class Meta:
        model = Owner
        fields = ['id', 'hospital_id', 'name', 'phone', 'email',
                  'age', 'gender', 'blood_group', 'address',
                  'is_primary', 'status', 'created_at']

    def _p(self, obj, field, default):
        p = getattr(obj.user, 'patient_profile', None)
        return getattr(p, field, default) if p else default

    def get_email(self, obj):       return obj.user.email or ''
    def get_age(self, obj):         return self._p(obj, 'age', 0)
    def get_gender(self, obj):      return self._p(obj, 'gender', '')
    def get_blood_group(self, obj): return self._p(obj, 'blood_group', '')
    def get_address(self, obj):     return self._p(obj, 'address', '')
