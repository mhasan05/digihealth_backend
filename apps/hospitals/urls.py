from django.urls import path
from .views import AdminDashboardView, HospitalListView, HospitalDetailView, HospitalToggleStatusView
from apps.staff.views import AdminDoctorListView, AdminDoctorDetailView, AdminDoctorAvailabilityView
from apps.role_applications.views import (
    AdminRoleApplicationListView, AdminRoleApplicationApproveView, AdminRoleApplicationRejectView,
)

urlpatterns = [
    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('hospitals/', HospitalListView.as_view(), name='admin-hospital-list'),
    path('hospitals/<uuid:pk>/', HospitalDetailView.as_view(), name='admin-hospital-detail'),
    path('hospitals/<uuid:pk>/toggle-status/', HospitalToggleStatusView.as_view(), name='admin-hospital-toggle'),
    path('doctors/', AdminDoctorListView.as_view(), name='admin-doctor-list'),
    path('doctors/<uuid:pk>/', AdminDoctorDetailView.as_view(), name='admin-doctor-detail'),
    path('doctors/<uuid:pk>/availability/', AdminDoctorAvailabilityView.as_view(), name='admin-doctor-availability'),
    path('role-applications/', AdminRoleApplicationListView.as_view(), name='admin-role-application-list'),
    path('role-applications/<uuid:pk>/approve/', AdminRoleApplicationApproveView.as_view(), name='admin-role-application-approve'),
    path('role-applications/<uuid:pk>/reject/', AdminRoleApplicationRejectView.as_view(), name='admin-role-application-reject'),
]
