import logging

from django.conf import settings
from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from apps.identity.services import IdentityService
from apps.parties.identity import is_identity_required
from common.responses import ok

logger = logging.getLogger("kotoku")


def _get_party_or_404(agreement_id: int, role: str, account):
    try:
        agreement = AgreementSelector.get_agreement_detail(
            agreement_id,
            account_id=account.pk,
            account_phone=account.phone,
        )
    except Agreement.DoesNotExist:
        raise Http404

    party = agreement.parties.filter(role=role).first()
    if party is None or not is_identity_required(party.role):
        raise Http404
    return party


class LivenessSessionView(APIView):
    """POST /api/agreements/<id>/identity/<role>/liveness-session/

    Creates an AWS Rekognition Face Liveness session for a party.
    The mobile client passes the returned session_id to FaceLivenessDetector.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int, role: str):
        party = _get_party_or_404(agreement_id, role, request.user.account)
        session_id = IdentityService.create_liveness_session(party=party)
        region = (
            getattr(settings, "AWS_REKOGNITION_REGION_NAME", None)
            or settings.AWS_S3_REGION_NAME.strip()
        )
        logger.info(
            "[IDENTITY] liveness_session_view agreement=%s role=%s",
            agreement_id,
            role,
        )
        return ok({"session_id": session_id, "region": region}, status_code=201)


class LivenessResultView(APIView):
    """POST /api/agreements/<id>/identity/<role>/liveness-result/

    Fetches the liveness session result from AWS, persists it, and queues card
    verification if the check passed and card images are already uploaded.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int, role: str):
        party = _get_party_or_404(agreement_id, role, request.user.account)
        result = IdentityService.process_liveness_result(party=party)
        logger.info(
            "[IDENTITY] liveness_result_view agreement=%s role=%s status=%s",
            agreement_id,
            role,
            result["status"],
        )
        return ok(result)
