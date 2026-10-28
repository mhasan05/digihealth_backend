from django.utils import timezone

from .models import FieldPrescription


def link_field_prescriptions(user):
    """Attach every unclaimed field prescription for `user.phone` to their
    patient profile. Returns the number linked.

    Runs on registration and whenever a prescription is uploaded for a number
    that already has an account. When SMS verification is added, the check
    that the phone was confirmed belongs here.
    """
    from apps.patients.models import Patient

    patient = Patient.objects.filter(user=user).first()
    if patient is None:
        return 0
    return FieldPrescription.objects.filter(
        phone=user.phone, status='unclaimed', patient__isnull=True,
    ).update(patient=patient, status='claimed', claimed_at=timezone.now())
