import uuid
from django.db import models
from django.conf import settings
from apps.hospitals.models import Hospital
from apps.patients.models import Patient
from apps.staff.models import Doctor, Nurse, Pathologist


class Bed(models.Model):
    TYPE_CHOICES = [
        ('General', 'General'),
        ('ICU', 'ICU'),
        ('Private', 'Private'),
        ('Cabin', 'Cabin'),
    ]
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Occupied', 'Occupied'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='hospital_beds')
    number = models.CharField(max_length=20)
    ward = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='General')
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Available')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clinical_bed'
        ordering = ['number']

    def __str__(self):
        return f"Bed {self.number} ({self.ward})"


class LabTest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='lab_tests')
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration = models.CharField(max_length=100, default='')
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clinical_lab_test'
        ordering = ['name']

    def __str__(self):
        return self.name


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='appointments')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, related_name='appointments')
    date = models.DateField()
    time = models.CharField(max_length=10)
    reason = models.TextField(default='')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')
    admitted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clinical_appointment'
        ordering = ['-created_at']

    def __str__(self):
        return f"Appointment: {self.patient.user.name} with Dr. {self.doctor.name if self.doctor else 'N/A'}"


class Admission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='admission')
    bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, related_name='admissions')
    nurse = models.ForeignKey(Nurse, on_delete=models.SET_NULL, null=True, related_name='admissions')
    admitted_at = models.DateTimeField(auto_now_add=True)
    discharged_at = models.DateTimeField(null=True, blank=True)
    bed_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'clinical_admission'
        ordering = ['-admitted_at']

    def __str__(self):
        return f"Admission: {self.appointment.patient.user.name}"


class LabOrder(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Assigned', 'Assigned'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='lab_orders')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_orders')
    test = models.ForeignKey(LabTest, on_delete=models.SET_NULL, null=True, related_name='lab_orders')
    ordered_by_doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordered_lab_orders')
    assigned_pathologist = models.ForeignKey(Pathologist, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_lab_orders')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clinical_lab_order'
        ordering = ['-created_at']

    def __str__(self):
        return f"LabOrder: {self.patient.user.name} - {self.test.name if self.test else 'N/A'}"


class LabResult(models.Model):
    REMARKS_CHOICES = [
        ('Normal', 'Normal'),
        ('Abnormal', 'Abnormal'),
        ('Follow-up required', 'Follow-up required'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lab_order = models.OneToOneField(LabOrder, on_delete=models.CASCADE, related_name='result')
    findings = models.TextField()
    remarks = models.CharField(max_length=30, choices=REMARKS_CHOICES, default='Normal')
    submitted_at = models.DateTimeField(auto_now_add=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='submitted_results')

    class Meta:
        db_table = 'clinical_lab_result'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Result for {self.lab_order}"
