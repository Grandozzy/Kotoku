import os
import sys
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.agreements.models import Agreement

drafts = Agreement.objects.filter(status='draft')[:3]
for d in drafts:
    print(f'ID: {d.id}, scenario_template: "{d.scenario_template}"')