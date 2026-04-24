import pytest

from apps.templates.models import ScenarioTemplate
from apps.templates.selectors import TemplateSelector


@pytest.mark.django_db
class TestTemplateSelector:
    def test_list_templates_returns_all(self):
        ScenarioTemplate.objects.create(
            slug="used_vehicle_sale",
            name="Used Vehicle Sale",
            description="Agreement for buying/selling a used vehicle",
            field_definitions={"vehicle_make": {"type": "string", "required": True}},
        )
        ScenarioTemplate.objects.create(
            slug="rental_agreement",
            name="Rental Agreement",
            description="Agreement for renting a property or vehicle",
            field_definitions={"rental_period": {"type": "string", "required": True}},
        )
        result = TemplateSelector.list_templates()
        assert result.count() == 2

    def test_get_by_slug_returns_template(self):
        ScenarioTemplate.objects.create(
            slug="used_vehicle_sale",
            name="Used Vehicle Sale",
            description="desc",
            field_definitions={},
        )
        template = TemplateSelector.get_by_slug("used_vehicle_sale")
        assert template.slug == "used_vehicle_sale"

    def test_get_by_slug_not_found_raises(self):
        with pytest.raises(ScenarioTemplate.DoesNotExist):
            TemplateSelector.get_by_slug("nonexistent")
