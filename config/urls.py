from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
