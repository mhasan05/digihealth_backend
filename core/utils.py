import random


def get_hospital_for_owner(user):
    """Get the Owner profile for the authenticated owner user."""
    from apps.hospitals.models import Owner
    return Owner.objects.filter(user=user).select_related('hospital').first()


def get_manager_profile(user):
    from apps.staff.models import Manager
    return Manager.objects.filter(user=user).select_related('hospital').first()


def get_pathologist_profile(user):
    from apps.staff.models import Pathologist
    return Pathologist.objects.filter(user=user).select_related('hospital').first()


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
