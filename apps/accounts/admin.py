from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ActivityEvent


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display    = ('name', 'phone', 'health_id', 'roles', 'is_active', 'is_staff', 'date_joined')
    list_filter     = ('is_active', 'is_staff', 'is_superuser')
    search_fields   = ('name', 'phone', 'health_id', 'email')
    ordering        = ('-date_joined',)
    readonly_fields = ('id', 'date_joined')

    fieldsets = (
        (None,            {'fields': ('phone', 'password')}),
        ('Personal Info', {'fields': ('name', 'email', 'health_id', 'roles')}),
        ('Permissions',   {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Metadata',      {'fields': ('id', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'name', 'health_id', 'roles', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display    = ('type', 'description', 'timestamp')
    list_filter     = ('type',)
    search_fields   = ('type', 'description')
    readonly_fields = ('id', 'timestamp')
    ordering        = ('-timestamp',)
