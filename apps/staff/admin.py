from django.contrib import admin
from .models import Manager, Pathologist, Doctor, HospitalDoctor, Nurse


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display    = ('user', 'hospital', 'status', 'created_at')
    list_filter     = ('status', 'hospital')
    search_fields   = ('user__name', 'user__phone', 'hospital__name_en')
    readonly_fields = ('id', 'created_at')
    raw_id_fields   = ('user', 'hospital')


@admin.register(Pathologist)
class PathologistAdmin(admin.ModelAdmin):
    list_display    = ('user', 'hospital', 'specialization', 'status', 'created_at')
    list_filter     = ('status', 'hospital')
    search_fields   = ('user__name', 'user__phone', 'specialization', 'hospital__name_en')
    readonly_fields = ('id', 'created_at')
    raw_id_fields   = ('user', 'hospital')


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display    = ('name', 'phone', 'bmdc_registration_no', 'specialization', 'availability_status', 'created_at')
    list_filter     = ('availability_status',)
    search_fields   = ('name', 'phone', 'bmdc_registration_no', 'specialization')
    readonly_fields = ('id', 'created_at')


@admin.register(HospitalDoctor)
class HospitalDoctorAdmin(admin.ModelAdmin):
    list_display    = ('doctor', 'hospital', 'schedule', 'status', 'attached_at')
    list_filter     = ('status', 'hospital')
    search_fields   = ('doctor__name', 'doctor__phone', 'doctor__bmdc_registration_no', 'hospital__name_en')
    readonly_fields = ('id', 'attached_at')
    raw_id_fields   = ('hospital', 'doctor')


@admin.register(Nurse)
class NurseAdmin(admin.ModelAdmin):
    list_display    = ('name', 'hospital', 'ward', 'phone', 'status', 'created_at')
    list_filter     = ('status', 'hospital')
    search_fields   = ('name', 'phone', 'ward', 'hospital__name_en')
    readonly_fields = ('id', 'created_at')
    raw_id_fields   = ('hospital',)
