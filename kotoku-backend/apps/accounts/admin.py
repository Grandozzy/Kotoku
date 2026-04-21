from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Account, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "phone", "is_active", "is_staff", "created_at")
    search_fields = ("phone",)
    ordering = ("id",)

    fieldsets = (
        (None, {"fields": ("phone",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )

    add_fieldsets = (
        (None, {"fields": ("phone",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser")},
        ),
    )


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "full_name", "phone", "user", "created_at")
    search_fields = ("email", "full_name", "phone")
    raw_id_fields = ("user",)
