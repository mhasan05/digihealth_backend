from django.urls import path
from .views import FieldMeView, FieldPhoneLookupView, FieldPrescriptionListView

# These are the /api/field/* routes (mobile app)
urlpatterns = [
    path('me/', FieldMeView.as_view(), name='field-me'),
    path('lookup/', FieldPhoneLookupView.as_view(), name='field-phone-lookup'),
    path('prescriptions/', FieldPrescriptionListView.as_view(), name='field-prescription-list'),
]
