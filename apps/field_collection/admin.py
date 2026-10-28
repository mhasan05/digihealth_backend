from django.contrib import admin
from .models import FieldStaff, FieldPrescription, FieldPrescriptionImage


@admin.register(FieldStaff)
class FieldStaffAdmin(admin.ModelAdmin):
    list_display  = ('user', 'area', 'status', 'created_at')
    list_filter   = ('status',)
    search_fields = ('user__name', 'user__phone', 'area')
    raw_id_fields = ('user', 'created_by')


class FieldPrescriptionImageInline(admin.TabularInline):
    model = FieldPrescriptionImage
    extra = 0
    readonly_fields = ('id', 'size', 'content_type', 'uploaded_at')


@admin.register(FieldPrescription)
class FieldPrescriptionAdmin(admin.ModelAdmin):
    list_display    = ('phone', 'patient_name', 'status', 'collected_by', 'collected_at')
    list_filter     = ('status',)
    search_fields   = ('phone', 'patient_name')
    readonly_fields = ('id', 'collected_at', 'claimed_at')
    raw_id_fields   = ('collected_by', 'patient')
    inlines         = [FieldPrescriptionImageInline]
