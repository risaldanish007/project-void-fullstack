from rest_framework.permissions import BasePermission

class IsAdminUserOrStaff(BasePermission):
    """
    Allows access only to authenticated users who have administrative / staff privileges.
    """
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )

