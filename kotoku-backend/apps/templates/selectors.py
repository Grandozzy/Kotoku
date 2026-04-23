from apps.templates.models import ScenarioTemplate
from common.exceptions import DomainError


class TemplateSelector:
    @staticmethod
    def list_templates():
        return ScenarioTemplate.objects.filter(is_active=True).order_by("name")

    @staticmethod
    def get_by_slug(slug: str) -> ScenarioTemplate:
        try:
            return ScenarioTemplate.objects.get(slug=slug, is_active=True)
        except ScenarioTemplate.DoesNotExist:
            raise DomainError(f"Template '{slug}' not found") from None
