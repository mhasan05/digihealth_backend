import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Phone number is required')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('roles', ['admin'])
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    health_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    roles = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    # Latest privacy notice version this user agreed to (see core/consent.py);
    # ConsentRecord keeps the full history.
    consent_version = models.CharField(max_length=40, blank=True, default='')
    consent_accepted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'accounts_user'

    def __str__(self):
        return f"{self.name} ({self.phone})"


class ActivityEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=100)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_activity_event'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.type}: {self.description}"


class ConsentRecord(models.Model):
    """One row per acceptance of the privacy & consent notice — the proof of
    what a user agreed to, when, and from where. Never updated or deleted."""
    CHANNEL_CHOICES = [
        ('register', 'Sign-up'),
        ('login', 'Login'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consent_records')
    version = models.CharField(max_length=40)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    language = models.CharField(max_length=5, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_consent_record'
        ordering = ['-accepted_at']

    def __str__(self):
        return f"{self.user.phone} accepted {self.version} ({self.channel})"
