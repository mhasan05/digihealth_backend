from django.contrib import admin
from .models import Patient, HealthMetric, MedicalReport, ReportAccessLog


class HealthMetricInline(admin.TabularInline):
    model           = HealthMetric
    extra           = 0
    readonly_fields = ('id',)


class MedicalReportInline(admin.TabularInline):
    model           = MedicalReport
    extra           = 0
    readonly_fields = ('id', 'uploaded_at')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display    = ('user', 'age', 'gender', 'blood_group', 'subscription_tier', 'created_at')
    list_filter     = ('gender', 'blood_group', 'subscription_tier')
    search_fields   = ('user__name', 'user__phone', 'user__health_id')
    readonly_fields = ('id', 'created_at')
    raw_id_fields   = ('user',)
    inlines         = [HealthMetricInline, MedicalReportInline]


@admin.register(HealthMetric)
class HealthMetricAdmin(admin.ModelAdmin):
    list_display    = ('patient', 'metric_type', 'value', 'date')
    list_filter     = ('metric_type',)
    search_fields   = ('patient__user__name', 'value')
    readonly_fields = ('id',)
    raw_id_fields   = ('patient',)


@admin.register(MedicalReport)
class MedicalReportAdmin(admin.ModelAdmin):
    list_display    = ('name', 'patient', 'size', 'uploaded_at')
    search_fields   = ('name', 'patient__user__name')
    readonly_fields = ('id', 'uploaded_at')
    raw_id_fields   = ('patient',)


@admin.register(ReportAccessLog)
class ReportAccessLogAdmin(admin.ModelAdmin):
    list_display    = ('accessor', 'accessor_role', 'action', 'report', 'patient', 'timestamp')
    list_filter     = ('action', 'accessor_role')
    search_fields   = ('accessor__name', 'report__name', 'patient__user__name')
    readonly_fields = ('id', 'timestamp')
    raw_id_fields   = ('patient', 'report', 'accessor')
