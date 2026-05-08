from django.contrib import admin
from .models import Manager, Pathologist, Doctor, Nurse


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
    list_display    = ('name', 'hospital', 'specialization', 'phone', 'status', 'created_at')
    list_filter     = ('status', 'hospital')
    search_fields   = ('name', 'phone', 'specialization', 'hospital__name_en')
    readonly_fields = ('id', 'created_at')
    raw_id_fields   = ('hospital',)


@admin.register(Nurse)
class NurseAdmin(admin.ModelAdmin):
    list_display    = ('name', 'hospital', 'ward', 'phone', 'status', 'created_at')
    list_filter     = ('status', 'hospital')
    search_fields   = ('name', 'phone', 'ward', 'hospital__name_en')
    readonly_fields = ('id', 'created_at')
    raw_id_fields   = ('hospital',)
