from django.urls import path
from .views import (
    OwnerDashboardView,
    CoOwnerListView, CoOwnerDetailView,
    ManagerListView, ManagerDetailView,
    PathologistListView, PathologistDetailView,
    DoctorListView, DoctorDetailView, DoctorRegistrySearchView,
    NurseListView, NurseDetailView,
    BedListView, BedDetailView,
    LabTestListView, LabTestDetailView,
)

urlpatterns = [
    path('dashboard/', OwnerDashboardView.as_view(), name='owner-dashboard'),
    path('co-owners/', CoOwnerListView.as_view(), name='owner-co-owner-list'),
    path('co-owners/<uuid:pk>/', CoOwnerDetailView.as_view(), name='owner-co-owner-detail'),
    path('managers/', ManagerListView.as_view(), name='owner-manager-list'),
    path('managers/<uuid:pk>/', ManagerDetailView.as_view(), name='owner-manager-detail'),
    path('pathologists/', PathologistListView.as_view(), name='owner-pathologist-list'),
    path('pathologists/<uuid:pk>/', PathologistDetailView.as_view(), name='owner-pathologist-detail'),
    path('doctors/', DoctorListView.as_view(), name='owner-doctor-list'),
    path('doctors/search/', DoctorRegistrySearchView.as_view(), name='owner-doctor-registry-search'),
    path('doctors/<uuid:pk>/', DoctorDetailView.as_view(), name='owner-doctor-detail'),
    path('nurses/', NurseListView.as_view(), name='owner-nurse-list'),
    path('nurses/<uuid:pk>/', NurseDetailView.as_view(), name='owner-nurse-detail'),
    path('beds/', BedListView.as_view(), name='owner-bed-list'),
    path('beds/<uuid:pk>/', BedDetailView.as_view(), name='owner-bed-detail'),
    path('lab-tests/', LabTestListView.as_view(), name='owner-labtest-list'),
    path('lab-tests/<uuid:pk>/', LabTestDetailView.as_view(), name='owner-labtest-detail'),
]
