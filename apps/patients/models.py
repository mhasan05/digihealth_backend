import uuid
from django.db import models
from django.conf import settings


class Patient(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    SUBSCRIPTION_CHOICES = [
        ('Free', 'Free'),
        ('Premium', 'Premium'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_profile')
    age = models.IntegerField(default=0)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Other')
    blood_group = models.CharField(max_length=10, default='Unknown')
    address = models.TextField(blank=True, default='')
    subscription_tier = models.CharField(max_length=10, choices=SUBSCRIPTION_CHOICES, default='Free')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'patients_patient'
        ordering = ['-created_at']

    def __str__(self):
        return f"Patient: {self.user.name}"


class HealthMetric(models.Model):
    METRIC_TYPE_CHOICES = [
        ('hba1c', 'HbA1c'),
        ('blood_pressure', 'Blood Pressure'),
        ('weight', 'Weight'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='health_metrics')
    metric_type = models.CharField(max_length=30, choices=METRIC_TYPE_CHOICES)
    date = models.DateField()
    value = models.CharField(max_length=100)

    class Meta:
        db_table = 'patients_health_metric'
        ordering = ['-date']

    def __str__(self):
        return f"{self.metric_type}: {self.value} ({self.date})"


class MedicalReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_reports')
    name = models.CharField(max_length=300)
    file_url = models.CharField(max_length=500)
    size = models.BigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'patients_medical_report'
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.name


class ReportAccessLog(models.Model):
    ACTION_CHOICES = [
        ('viewed', 'Viewed'),
        ('downloaded', 'Downloaded'),
        ('shared', 'Shared'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='access_logs')
    report = models.ForeignKey(MedicalReport, on_delete=models.CASCADE, related_name='access_logs')
    accessor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='report_access_logs')
    accessor_role = models.CharField(max_length=20)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'patients_report_access_log'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.accessor.name} {self.action} {self.report.name}"
