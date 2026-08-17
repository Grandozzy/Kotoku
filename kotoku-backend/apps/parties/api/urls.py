from django.urls import path

from .views import InviteClaimView, InviteDetailView, PartyInviteSendView, PartiesView

urlpatterns = [
    path("", PartiesView.as_view(), name="agreement-parties"),
    path(
        "invite/<str:role>/",
        PartyInviteSendView.as_view(),
        name="agreement-party-invite-send",
    ),
]

# Mounted separately at /api/invites/ in config/urls.py
invite_urlpatterns = [
    path("<str:token>/", InviteDetailView.as_view(), name="invite-detail"),
    path("<str:token>/claim/", InviteClaimView.as_view(), name="invite-claim"),
]
