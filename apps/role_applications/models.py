import uuid
from django.db import models
from django.conf import settings


def role_application_upload_path(instance, filename):
    health_id = getattr(instance.applicant, 'health_id', None) or 'unknown'
    return f'role_applications/{health_id}/{instance.role_type}/{filename}'


class RoleApplication(models.Model):
    """A patient's self-service request for an additional role.

    Admin reviews and approves/rejects. On approval, the relevant registry/staff
    row is created (Doctor registry entry, unattached Nurse/MedicalAssistant/
    Midwife row, or a brand-new Hospital+Owner for organization_owner) — see
    apps/role_applications/views.py `AdminRoleApplicationApproveView`.
    """

    ROLE_TYPE_CHOICES = [
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('medical_assistant', 'Medical Assistant'),
        ('midwife', 'Midwife'),
        ('pathologist', 'Pathologist'),
        ('organization_owner', 'Organization Owner'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    ORG_TYPE_CHOICES = [
        ('Diagnostic', 'Diagnostic'),
        ('Clinic', 'Clinic'),
        ('Hospital', 'Hospital'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='role_applications',
    )
    role_type = models.CharField(max_length=30, choices=ROLE_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')

    # Doctor / Nurse / Medical Assistant / Midwife — also reused as the
    # organization's registration number for organization_owner applications.
    registration_number = models.CharField(max_length=100, blank=True, default='')
    # Generic proof-of-license document (staff roles) or "Photo Upload Of
    # Registration" (organization_owner).
    document = models.FileField(upload_to=role_application_upload_path, null=True, blank=True)
    # organization_owner only — "Photo Of The Facility".
    facility_photo = models.FileField(upload_to=role_application_upload_path, null=True, blank=True)

    # ── organization_owner-only fields ──────────────────────────────────────
    org_name = models.CharField(max_length=200, blank=True, default='')
    org_type = models.CharField(max_length=20, choices=ORG_TYPE_CHOICES, blank=True, default='')
    validity_till = models.DateField(null=True, blank=True)
    org_phone = models.CharField(max_length=20, blank=True, default='')
    location_text = models.CharField(max_length=300, blank=True, default='')
    upazilla = models.CharField(max_length=100, blank=True, default='')
    district = models.CharField(max_length=100, blank=True, default='')
    division = models.CharField(max_length=100, blank=True, default='')
    post_code = models.CharField(max_length=20, blank=True, default='')

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_role_applications',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'role_applications_application'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_role_type_display()} application: {self.applicant.name} ({self.status})"
