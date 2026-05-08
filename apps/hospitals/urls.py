from django.urls import path
from .views import AdminDashboardView, HospitalListView, HospitalDetailView, HospitalToggleStatusView

urlpatterns = [
    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('hospitals/', HospitalListView.as_view(), name='admin-hospital-list'),
    path('hospitals/<uuid:pk>/', HospitalDetailView.as_view(), name='admin-hospital-detail'),
    path('hospitals/<uuid:pk>/toggle-status/', HospitalToggleStatusView.as_view(), name='admin-hospital-toggle'),
]
