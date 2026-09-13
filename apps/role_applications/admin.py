from django.contrib import admin
from .models import RoleApplication


@admin.register(RoleApplication)
class RoleApplicationAdmin(admin.ModelAdmin):
    list_display    = ('applicant', 'role_type', 'status', 'registration_number', 'created_at', 'reviewed_at')
    list_filter     = ('role_type', 'status')
    search_fields   = ('applicant__name', 'applicant__phone', 'registration_number', 'org_name')
    readonly_fields = ('id', 'created_at')
    raw_id_fields   = ('applicant', 'reviewed_by')
