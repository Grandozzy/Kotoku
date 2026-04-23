from rest_framework import serializers

from apps.templates.models import ScenarioTemplate


class ScenarioTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScenarioTemplate
        fields = ("slug", "name", "description", "field_definitions", "version", "updated_at")
