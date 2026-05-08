import uuid
from django.db import models
from django.conf import settings
from apps.hospitals.models import Hospital


class Manager(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('On-leave', 'On-leave'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='manager_profiles')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='managers')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staff_manager'
        ordering = ['-created_at']

    def __str__(self):
        return f"Manager: {self.user.name}"


class Pathologist(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pathologist_profiles')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='pathologists')
    specialization = models.CharField(max_length=200, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staff_pathologist'
        ordering = ['-created_at']

    def __str__(self):
        return f"Pathologist: {self.user.name}"


class Doctor(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='doctors')
    name = models.CharField(max_length=200)
    specialization = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    schedule = models.CharField(max_length=200, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staff_doctor'
        ordering = ['-created_at']

    def __str__(self):
        return f"Dr. {self.name}"


class Nurse(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('On-leave', 'On-leave'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='nurses')
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    ward = models.CharField(max_length=100, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staff_nurse'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
