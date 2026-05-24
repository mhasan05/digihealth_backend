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

    HIV_STATUS_CHOICES = [
        ('Negative', 'Negative'),
        ('Positive', 'Positive'),
    ]

    # Allowed slugs for `conditions`. Keep additive-only — old rows store
    # whichever slugs were valid at the time.
    CONDITION_CHOICES = ['asthma', 'hypertension', 'diabetes', 'ckd']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_profile')
    age = models.IntegerField(default=0)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Other')
    blood_group = models.CharField(max_length=10, default='Unknown')
    address = models.TextField(blank=True, default='')
    subscription_tier = models.CharField(max_length=10, choices=SUBSCRIPTION_CHOICES, default='Free')
    hiv_status = models.CharField(max_length=10, choices=HIV_STATUS_CHOICES, default='Negative')
    # When True, the patient is hidden from doctor search and detail/report endpoints.
    # Owner-controlled by the patient themselves from their portal.
    is_private = models.BooleanField(default=False)
    # Self-reported chronic conditions — list of slugs from CONDITION_CHOICES.
    # Doctors see these on patient lookup. Patient toggles from their settings.
    conditions = models.JSONField(default=list, blank=True)
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


def report_upload_path(instance, filename):
    health_id = getattr(getattr(instance.patient, 'user', None), 'health_id', None) or 'unknown'
    return f'reports/{health_id}/{filename}'


class MedicalReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_reports')
    name = models.CharField(max_length=300)
    file = models.FileField(upload_to=report_upload_path, null=True, blank=True)
    size = models.BigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'patients_medical_report'
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.name


class ReportAccessLog(models.Model):
    ACTION_CHOICES = [
        ('searched', 'Searched'),
        ('viewed', 'Viewed'),
        ('downloaded', 'Downloaded'),
        ('shared', 'Shared'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='access_logs')
    # 'searched' events log a lookup of the patient itself, not a specific report,
    # so report can be null.
    report = models.ForeignKey(
        MedicalReport, on_delete=models.CASCADE, related_name='access_logs',
        null=True, blank=True,
    )
    accessor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='report_access_logs')
    accessor_role = models.CharField(max_length=20)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'patients_report_access_log'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.accessor.name} {self.action} {self.report.name}"
