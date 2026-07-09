import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

from common.exceptions import ServiceUnavailableError

logger = logging.getLogger("kotoku")


def _get_client():
    client_kwargs = {
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        "region_name": settings.AWS_S3_REGION_NAME.strip(),
    }
    session_token = getattr(settings, "AWS_SESSION_TOKEN", "")
    if session_token:
        client_kwargs["aws_session_token"] = session_token
    return boto3.client("rekognition", **client_kwargs)


class RekognitionClient:
    def compare_faces(
        self,
        *,
        source_bytes: bytes,
        target_bytes: bytes,
        similarity_threshold: float = 70.0,
    ) -> dict:
        try:
            response = _get_client().compare_faces(
                SourceImage={"Bytes": source_bytes},
                TargetImage={"Bytes": target_bytes},
                SimilarityThreshold=similarity_threshold,
            )
        except (BotoCoreError, ClientError) as exc:
            logger.warning(
                "[IDENTITY] rekognition_compare_faces_error type=%s",
                exc.__class__.__name__,
            )
            raise ServiceUnavailableError(
                "Face verification is temporarily unavailable. Please try again later."
            ) from exc

        matches = response.get("FaceMatches", [])
        best_match = max(matches, key=lambda item: float(item.get("Similarity", 0.0)), default=None)
        return {
            "source_face_confidence": float(
                response.get("SourceImageFace", {}).get("Confidence", 0.0)
            ),
            "similarity": float(best_match.get("Similarity", 0.0)) if best_match else 0.0,
            "face_matches_count": len(matches),
            "unmatched_faces_count": len(response.get("UnmatchedFaces", [])),
        }
