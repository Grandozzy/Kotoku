from django.db import models


class ConsentRecord(models.Model):
    granted = models.BooleanField(default=False)
