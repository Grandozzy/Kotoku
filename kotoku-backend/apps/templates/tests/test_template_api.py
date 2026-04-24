import pytest
from rest_framework.test import APIClient

from apps.templates.models import ScenarioTemplate


@pytest.mark.django_db
class TestTemplateListApi:
    def test_list_templates_returns_200(self):
        ScenarioTemplate.objects.create(
            slug="used_vehicle_sale", name="Used Vehicle Sale", field_definitions={}
        )
        ScenarioTemplate.objects.create(
            slug="rental_agreement", name="Rental Agreement", field_definitions={}
        )
        response = APIClient().get("/api/templates/", format="json")
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) == 2

    def test_list_templates_empty(self):
        response = APIClient().get("/api/templates/", format="json")
        assert response.status_code == 200


@pytest.mark.django_db
class TestTemplateDetailApi:
    def test_get_template_by_slug_returns_200(self):
        ScenarioTemplate.objects.create(
            slug="used_vehicle_sale",
            name="Used Vehicle Sale",
            field_definitions={"vehicle_make": {"type": "string"}},
        )
        response = APIClient().get("/api/templates/used_vehicle_sale/", format="json")
        assert response.status_code == 200
        data = response.json()["data"]["template"]
        assert data["slug"] == "used_vehicle_sale"
        assert "vehicle_make" in data["field_definitions"]

    def test_get_template_not_found_returns_404(self):
        response = APIClient().get("/api/templates/nonexistent/", format="json")
        assert response.status_code == 404
