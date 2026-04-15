from rest_framework.permissions import BasePermission


class IsSystemHealthy(BasePermission):
    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        return True
