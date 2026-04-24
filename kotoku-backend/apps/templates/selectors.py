from apps.templates.models import ScenarioTemplate


class TemplateSelector:
    @staticmethod
    def list_templates():
        return ScenarioTemplate.objects.filter(is_active=True).order_by("name")

    @staticmethod
    def get_by_slug(slug: str) -> ScenarioTemplate:
        return ScenarioTemplate.objects.get(slug=slug, is_active=True)
