from django.contrib import admin
from .models import Bed, LabTest, Appointment, Admission, LabOrder, LabResult


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display    = ('number', 'hospital', 'ward', 'type', 'price_per_day', 'status', 'created_at')
    list_filter     = ('type', 'status', 'hospital')
    search_fields   = ('number', 'ward', 'hospital__name_en')
    readonly_fields = ('id', 'created_at')
    raw_id_fields   = ('hospital',)


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display    = ('name', 'hospital', 'price', 'duration', 'available', 'created_at')
    list_filter     = ('available', 'hospital')
    search_fields   = ('name', 'hospital__name_en')
    readonly_fields = ('id', 'created_at')
    raw_id_fields   = ('hospital',)


class AdmissionInline(admin.StackedInline):
    model           = Admission
    extra           = 0
    readonly_fields = ('id', 'admitted_at', 'bed_price_snapshot')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display    = ('patient', 'doctor', 'hospital', 'date', 'time', 'status', 'admitted', 'created_at')
    list_filter     = ('status', 'admitted', 'hospital', 'date')
    search_fields   = ('patient__user__name', 'doctor__name', 'hospital__name_en', 'reason')
    readonly_fields = ('id', 'created_at')
    raw_id_fields   = ('hospital', 'patient', 'doctor')
    inlines         = [AdmissionInline]


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display    = ('appointment', 'bed', 'nurse', 'admitted_at', 'discharged_at', 'bed_price_snapshot')
    list_filter     = ('bed__hospital',)
    search_fields   = ('appointment__patient__user__name', 'bed__number', 'nurse__name')
    readonly_fields = ('id', 'admitted_at', 'bed_price_snapshot')
    raw_id_fields   = ('appointment', 'bed', 'nurse')


class LabResultInline(admin.StackedInline):
    model           = LabResult
    extra           = 0
    readonly_fields = ('id', 'submitted_at')


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display    = ('patient', 'test', 'hospital', 'assigned_pathologist', 'status', 'created_at')
    list_filter     = ('status', 'hospital')
    search_fields   = ('patient__user__name', 'test__name', 'hospital__name_en')
    readonly_fields = ('id', 'created_at')
    raw_id_fields   = ('hospital', 'patient', 'test', 'ordered_by_doctor', 'assigned_pathologist')
    inlines         = [LabResultInline]


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display    = ('lab_order', 'remarks', 'submitted_by', 'submitted_at')
    list_filter     = ('remarks',)
    search_fields   = ('lab_order__patient__user__name', 'findings')
    readonly_fields = ('id', 'submitted_at')
    raw_id_fields   = ('lab_order', 'submitted_by')
