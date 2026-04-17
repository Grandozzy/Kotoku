from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "full_name", "phone", "created_at")
    search_fields = ("email", "full_name", "phone")
