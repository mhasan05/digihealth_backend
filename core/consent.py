"""Privacy & consent notice shown to patients at sign-up and first login.

Bump CURRENT_CONSENT_VERSION whenever the notice text changes (the web app's
src/lib/consent-notice.ts must use the same value): every patient is then
asked to agree again on their next visit.
"""
from django.utils import timezone

CURRENT_CONSENT_VERSION = '2026-11-17'


def needs_consent(user):
    """Patients must have agreed to the current notice. Staff-only accounts
    (admin, owner, field staff…) don't store their own health records here."""
    return 'patient' in (user.roles or []) and user.consent_version != CURRENT_CONSENT_VERSION


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[0].strip() or request.META.get('REMOTE_ADDR') or None


def record_consent(user, request, channel, language=''):
    from apps.accounts.models import ConsentRecord

    now = timezone.now()
    ConsentRecord.objects.create(
        user=user,
        version=CURRENT_CONSENT_VERSION,
        channel=channel,
        language=(language or '')[:5],
        ip_address=_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:1000],
    )
    user.consent_version = CURRENT_CONSENT_VERSION
    user.consent_accepted_at = now
    user.save(update_fields=['consent_version', 'consent_accepted_at'])
