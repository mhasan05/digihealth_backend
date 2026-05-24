from django.contrib import admin
from django.urls import path, include
from apps.patients.views import ReportFileView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth endpoints
    path('api/auth/', include('apps.accounts.urls')),
    # Admin portal (hospitals management)
    path('api/admin/', include('apps.hospitals.urls')),
    # Owner portal (staff, beds, lab tests)
    path('api/owner/', include('apps.staff.urls')),
    # Manager portal (appointments, admissions, lab orders)
    path('api/manager/', include('apps.clinical.urls')),
    # Pathologist portal
    path('api/pathologist/', include('apps.patients.urls')),
    # Patient portal
    path('api/patient/', include('apps.finance.urls')),
    # Doctor portal
    path('api/doctor/', include('apps.staff.doctor_urls')),
    # Signed-URL file delivery for medical reports.
    # NOTE: We intentionally do NOT serve MEDIA_URL via django.conf.urls.static
    # here — that would expose /media/reports/<health_id>/<file> to anyone who
    # guesses the path. All medical-report bytes must go through this view.
    path('api/files/reports/', ReportFileView.as_view(), name='report-file'),
]
