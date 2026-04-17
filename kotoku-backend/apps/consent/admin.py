from django.contrib import admin

from .models import ConsentRecord


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "agreement", "party", "channel", "granted", "expires_at")
    list_select_related = ("agreement", "party")
    list_filter = ("channel", "granted")
