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
    """System-wide doctor registry. Managed by admin; owners attach via HospitalDoctor.

    `availability_status` is the global flag — Unavailable means the doctor is
    hidden from owner search and pinned to inactive across all hospitals.
    """

    AVAILABILITY_CHOICES = [
        ('Available', 'Available'),
        ('Unavailable', 'Unavailable'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='doctor_profile',
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    bmdc_registration_no = models.CharField(max_length=50, unique=True, null=True, blank=True)
    specialization = models.CharField(max_length=200, default='', blank=True)
    availability_status = models.CharField(max_length=12, choices=AVAILABILITY_CHOICES, default='Available')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staff_doctor'
        ordering = ['-created_at']

    def __str__(self):
        return f"Dr. {self.name}"


class HospitalDoctor(models.Model):
    """Per-hospital attachment of a registry doctor — only owner-tunable fields live here."""

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='doctor_attachments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='hospital_attachments')
    schedule = models.CharField(max_length=200, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    attached_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staff_hospital_doctor'
        ordering = ['-attached_at']
        unique_together = ('hospital', 'doctor')

    def __str__(self):
        return f"{self.doctor} @ {self.hospital}"


class Nurse(models.Model):
    """Hospital-scoped staff record.

    `hospital` is nullable to represent an admin-approved role-application
    that hasn't been imported into a hospital yet (see apps.role_applications).
    `user` is nullable too — nurses added directly by an owner (the original
    flow) have no backing account; nurses that came through an approved
    application are linked to the applicant's User.
    """

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('On-leave', 'On-leave'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(
        Hospital, on_delete=models.CASCADE, related_name='nurses', null=True, blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='nurse_profile',
    )
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


class MedicalAssistant(models.Model):
    """Mirrors Nurse — see its docstring for the nullable hospital/user rationale."""

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('On-leave', 'On-leave'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(
        Hospital, on_delete=models.CASCADE, related_name='medical_assistants', null=True, blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='medical_assistant_profile',
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    ward = models.CharField(max_length=100, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staff_medical_assistant'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Midwife(models.Model):
    """Mirrors Nurse — see its docstring for the nullable hospital/user rationale."""

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('On-leave', 'On-leave'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(
        Hospital, on_delete=models.CASCADE, related_name='midwives', null=True, blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='midwife_profile',
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    ward = models.CharField(max_length=100, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staff_midwife'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
