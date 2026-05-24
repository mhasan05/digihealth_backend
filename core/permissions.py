from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and 'admin' in request.user.roles


class IsOwner(BasePermission):
    """User must have 'owner' role."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and 'owner' in request.user.roles


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and 'manager' in request.user.roles


class IsPathologist(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and 'pathologist' in request.user.roles


class IsPatient(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and 'patient' in request.user.roles


class IsDoctor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and 'doctor' in request.user.roles
