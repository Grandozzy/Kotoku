from rest_framework import serializers

from apps.agreements.models import Annotation


class AnnotationCreateSerializer(serializers.Serializer):
    author_party_id = serializers.IntegerField()
    body = serializers.CharField(min_length=1, max_length=5000)


class AnnotationSerializer(serializers.ModelSerializer):
    author_party_id = serializers.IntegerField(source="author_party.pk", read_only=True)
    author_display_name = serializers.CharField(
        source="author_party.display_name", read_only=True
    )

    class Meta:
        model = Annotation
        fields = (
            "id",
            "author_party_id",
            "author_display_name",
            "body",
            "created_at",
        )
