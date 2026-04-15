from rest_framework.permissions import BasePermission


class IsAccountOwner(BasePermission):
    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        return bool(request.user and request.user.is_authenticated)
