"""Signed, short-lived tokens for medical report downloads.

The token IS the authorization — only people who got it via an auth-gated API
endpoint (patient's own list, or doctor's patient-scoped list) can use it. The
underlying file path on disk should NOT be reachable directly.
"""

from django.core.signing import TimestampSigner, BadSignature, SignatureExpired


REPORT_FILE_SALT = 'medical-report-file-v1'
REPORT_FILE_MAX_AGE_SECONDS = 30 * 60  # 30 minutes — long enough to click after the page loads.


def make_report_file_token(report_id) -> str:
    signer = TimestampSigner(salt=REPORT_FILE_SALT)
    return signer.sign(str(report_id))


def read_report_file_token(token: str, max_age: int = REPORT_FILE_MAX_AGE_SECONDS):
    """Return the verified report_id (str) or None if invalid/expired."""
    signer = TimestampSigner(salt=REPORT_FILE_SALT)
    try:
        return signer.unsign(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


ROLE_APPLICATION_FILE_SALT = 'role-application-file-v1'
ROLE_APPLICATION_FILE_MAX_AGE_SECONDS = 30 * 60


def make_role_application_file_token(application_id, field: str) -> str:
    signer = TimestampSigner(salt=ROLE_APPLICATION_FILE_SALT)
    return signer.sign(f'{application_id}:{field}')


def read_role_application_file_token(token: str, max_age: int = ROLE_APPLICATION_FILE_MAX_AGE_SECONDS):
    """Return the verified (application_id, field) tuple (str, str) or None if invalid/expired."""
    signer = TimestampSigner(salt=ROLE_APPLICATION_FILE_SALT)
    try:
        raw = signer.unsign(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    application_id, _, field = raw.partition(':')
    if not application_id or field not in ('document', 'facility_photo'):
        return None
    return application_id, field
