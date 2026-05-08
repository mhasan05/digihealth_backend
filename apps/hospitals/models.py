import uuid
from django.db import models
from django.conf import settings


class Hospital(models.Model):
    TYPE_CHOICES = [
        ('General', 'General'),
        ('Specialized', 'Specialized'),
        ('Clinic', 'Clinic'),
        ('Diagnostic', 'Diagnostic'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Paused', 'Paused'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_bn = models.CharField(max_length=300)
    name_en = models.CharField(max_length=300)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='General')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    beds = models.IntegerField(default=0)
    established = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hospitals_hospital'
        ordering = ['-created_at']

    def __str__(self):
        return self.name_en


class Owner(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owner_profiles')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='owners')
    is_primary = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hospitals_owner'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.name} - {self.hospital.name_en}"
