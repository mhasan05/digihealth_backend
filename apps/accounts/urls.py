from django.urls import path
from .views import LoginView, RegisterView, LogoutView, DemoLoginView
from apps.staff.views import ChangePasswordView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('demo-login/', DemoLoginView.as_view(), name='demo-login'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]
