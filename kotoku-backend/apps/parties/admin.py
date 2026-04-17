from django.contrib import admin

from .models import Party


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ("id", "display_name", "role", "agreement", "created_at")
