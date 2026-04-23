from django.core.management.base import BaseCommand

from apps.templates.models import ScenarioTemplate

TEMPLATES = [
    {
        "slug": "used_vehicle_sale",
        "name": "Used Vehicle Sale Agreement",
        "description": "Agreement for the sale and purchase of a used vehicle between two parties.",
        "field_definitions": {
            "vehicle_make": {"type": "string", "required": True, "label": "Vehicle Make"},
            "vehicle_model": {"type": "string", "required": True, "label": "Vehicle Model"},
            "vehicle_year": {"type": "integer", "required": True, "label": "Year of Manufacture"},
            "vin_chassis": {"type": "string", "required": True, "label": "VIN / Chassis Number"},
            "sale_price": {"type": "decimal", "required": True, "label": "Sale Price (GHS)"},
            "odometer_reading": {
                "type": "integer",
                "required": False,
                "label": "Odometer Reading (km)",
            },
            "payment_method": {
                "type": "choice",
                "required": True,
                "label": "Payment Method",
                "choices": ["cash", "bank_transfer", "mobile_money"],
            },
        },
    },
    {
        "slug": "rental_agreement",
        "name": "Rental Agreement",
        "description": "Agreement for renting a vehicle or property between two parties.",
        "field_definitions": {
            "item_description": {
                "type": "string",
                "required": True,
                "label": "Item Being Rented",
            },
            "rental_period_start": {
                "type": "date",
                "required": True,
                "label": "Rental Start Date",
            },
            "rental_period_end": {
                "type": "date",
                "required": True,
                "label": "Rental End Date",
            },
            "rental_amount": {
                "type": "decimal",
                "required": True,
                "label": "Rental Amount (GHS)",
            },
            "payment_schedule": {
                "type": "choice",
                "required": True,
                "label": "Payment Schedule",
                "choices": ["daily", "weekly", "monthly"],
            },
            "deposit_amount": {
                "type": "decimal",
                "required": False,
                "label": "Security Deposit (GHS)",
            },
        },
    },
]


class Command(BaseCommand):
    help = "Seed scenario templates for MVP"

    def handle(self, *args, **options):
        for template_data in TEMPLATES:
            obj, created = ScenarioTemplate.objects.update_or_create(
                slug=template_data["slug"],
                defaults={
                    "name": template_data["name"],
                    "description": template_data["description"],
                    "field_definitions": template_data["field_definitions"],
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} template: {obj.slug}")
        self.stdout.write(self.style.SUCCESS("Templates seeded successfully"))
