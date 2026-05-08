from django.contrib import admin
from .models import Hospital, Owner


class OwnerInline(admin.TabularInline):
    model           = Owner
    extra           = 0
    fields          = ('user', 'is_primary', 'status', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display    = ('name_en', 'name_bn', 'type', 'status', 'phone', 'beds', 'established', 'created_at')
    list_filter     = ('type', 'status')
    search_fields   = ('name_en', 'name_bn', 'phone', 'email', 'address')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines         = [OwnerInline]

    fieldsets = (
        ('Identity',    {'fields': ('id', 'name_en', 'name_bn', 'type', 'status')}),
        ('Contact',     {'fields': ('address', 'phone', 'email')}),
        ('Details',     {'fields': ('beds', 'established')}),
        ('Timestamps',  {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display    = ('user', 'hospital', 'is_primary', 'status', 'created_at')
    list_filter     = ('is_primary', 'status')
    search_fields   = ('user__name', 'user__phone', 'hospital__name_en')
    readonly_fields = ('id', 'created_at')
    raw_id_fields   = ('user', 'hospital')
