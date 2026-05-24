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
