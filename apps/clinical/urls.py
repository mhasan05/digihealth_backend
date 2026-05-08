from django.urls import path
from .views import (
    ManagerDashboardView,
    AppointmentListView, AppointmentDetailView,
    AppointmentConfirmView, AppointmentCancelView, AppointmentAdmitView,
    AdmissionListView, AvailableBedsView, AvailableNursesView,
    LabOrderListView, LabOrderAssignView, LabOrderCancelView, LabOrderResultView,
    ManagerDoctorsView, ManagerPatientsView, WalkInPatientView,
)

urlpatterns = [
    path('dashboard/', ManagerDashboardView.as_view(), name='manager-dashboard'),
    path('appointments/', AppointmentListView.as_view(), name='manager-appointment-list'),
    path('appointments/<uuid:pk>/', AppointmentDetailView.as_view(), name='manager-appointment-detail'),
    path('appointments/<uuid:pk>/confirm/', AppointmentConfirmView.as_view(), name='manager-appointment-confirm'),
    path('appointments/<uuid:pk>/cancel/', AppointmentCancelView.as_view(), name='manager-appointment-cancel'),
    path('appointments/<uuid:pk>/admit/', AppointmentAdmitView.as_view(), name='manager-appointment-admit'),
    path('admissions/', AdmissionListView.as_view(), name='manager-admission-list'),
    path('available-beds/', AvailableBedsView.as_view(), name='manager-available-beds'),
    path('available-nurses/', AvailableNursesView.as_view(), name='manager-available-nurses'),
    path('lab-orders/', LabOrderListView.as_view(), name='manager-lab-order-list'),
    path('lab-orders/<uuid:pk>/assign/', LabOrderAssignView.as_view(), name='manager-lab-order-assign'),
    path('lab-orders/<uuid:pk>/cancel/', LabOrderCancelView.as_view(), name='manager-lab-order-cancel'),
    path('lab-orders/<uuid:pk>/result/', LabOrderResultView.as_view(), name='manager-lab-order-result'),
    path('doctors/', ManagerDoctorsView.as_view(), name='manager-doctors'),
    path('patients/', ManagerPatientsView.as_view(), name='manager-patients'),
    path('walk-in-patient/', WalkInPatientView.as_view(), name='manager-walk-in-patient'),
]
