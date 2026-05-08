import random


def _first_active_hospital():
    """Pick a hospital to attach an orphaned profile to (Active first, else any)."""
    from apps.hospitals.models import Hospital
    return Hospital.objects.filter(status='Active').first() or Hospital.objects.first()


def get_hospital_for_owner(user):
    """Get the Owner profile for the authenticated owner user.

    If the user has 'owner' role but no Owner row, auto-attach to the first hospital
    so demo / partial-setup flows don't 404.
    """
    from apps.hospitals.models import Owner
    own = Owner.objects.filter(user=user).select_related('hospital').first()
    if own:
        return own
    if 'owner' in (user.roles or []):
        h = _first_active_hospital()
        if h:
            return Owner.objects.create(user=user, hospital=h, is_primary=False, status='Active')
    return None


def get_manager_profile(user):
    """Find the Manager profile, auto-creating one if user has the role but no row."""
    from apps.staff.models import Manager
    mgr = Manager.objects.filter(user=user).select_related('hospital').first()
    if mgr:
        return mgr
    if 'manager' in (user.roles or []):
        h = _first_active_hospital()
        if h:
            return Manager.objects.create(user=user, hospital=h, status='Active')
    return None


def get_pathologist_profile(user):
    """Find the Pathologist profile, auto-creating one if user has the role but no row."""
    from apps.staff.models import Pathologist
    p = Pathologist.objects.filter(user=user).select_related('hospital').first()
    if p:
        return p
    if 'pathologist' in (user.roles or []):
        h = _first_active_hospital()
        if h:
            return Pathologist.objects.create(user=user, hospital=h, specialization='General', status='Active')
    return None


def get_active_hospital_id(user):
    """Derive the active hospital UUID for any role."""
    if 'manager' in user.roles:
        mgr = get_manager_profile(user)
        return str(mgr.hospital_id) if mgr else None
    if 'owner' in user.roles:
        own = get_hospital_for_owner(user)
        return str(own.hospital_id) if own else None
    if 'pathologist' in user.roles:
        path = get_pathologist_profile(user)
        return str(path.hospital_id) if path else None
    return None


def generate_health_id():
    """Generate unique DH-XXXXXXXXXXXX health ID."""
    from apps.accounts.models import User
    while True:
        digits = ''.join([str(random.randint(0, 9)) for _ in range(12)])
        hid = f'DH-{digits}'
        if not User.objects.filter(health_id=hid).exists():
            return hid


# ── Demographics ──────────────────────────────────────────────────────────────

REQUIRED_DEMOGRAPHIC_FIELDS = ('age', 'gender', 'blood_group', 'address')

ALLOWED_GENDERS = ('Male', 'Female', 'Other')
ALLOWED_BLOOD_GROUPS = ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')


def validate_demographics(data, *, require=True):
    """Validate the personal-info fields used across owner/manager/pathologist/user.

    Returns (cleaned_dict, error_message_or_None). When require=False, missing
    fields are skipped (partial update) but provided values are still validated.
    """
    cleaned = {}

    if 'age' in data or require:
        raw = data.get('age')
        if raw in (None, ''):
            if require:
                return None, 'age is required.'
        else:
            try:
                age = int(raw)
            except (TypeError, ValueError):
                return None, 'age must be a number.'
            if age < 0 or age > 150:
                return None, 'age must be between 0 and 150.'
            cleaned['age'] = age

    if 'gender' in data or require:
        gender = (data.get('gender') or '').strip()
        if not gender:
            if require:
                return None, 'gender is required.'
        elif gender not in ALLOWED_GENDERS:
            return None, f'gender must be one of {ALLOWED_GENDERS}.'
        else:
            cleaned['gender'] = gender

    # blood_group is ALWAYS optional — many patients don't know their group.
    # If supplied, must be one of the allowed values; if blank, we just skip it.
    if 'blood_group' in data:
        bg = (data.get('blood_group') or '').strip()
        if bg and bg not in ALLOWED_BLOOD_GROUPS:
            return None, f'blood_group must be one of {ALLOWED_BLOOD_GROUPS}.'
        if bg:
            cleaned['blood_group'] = bg

    if 'address' in data or require:
        addr = (data.get('address') or '').strip()
        if not addr:
            if require:
                return None, 'address is required.'
        else:
            cleaned['address'] = addr

    return cleaned, None


def ensure_patient_profile(user, **demographics):
    """Create or update the Patient row that holds personal info for a user.

    Used when creating owner/manager/pathologist accounts so their demographics
    are stored consistently with patients. `demographics` is the cleaned dict
    returned by `validate_demographics`.
    """
    from apps.patients.models import Patient
    patient = Patient.objects.filter(user=user).first()
    if patient is None:
        patient = Patient.objects.create(
            user=user,
            age=demographics.get('age', 0),
            gender=demographics.get('gender', 'Other'),
            blood_group=demographics.get('blood_group', 'Unknown'),
            address=demographics.get('address', ''),
            subscription_tier='Free',
        )
    else:
        for k, v in demographics.items():
            setattr(patient, k, v)
        if demographics:
            patient.save()
    return patient
