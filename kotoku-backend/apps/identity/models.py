from django.db import models


class IdentityRecord(models.Model):
    reference = models.CharField(max_length=64, unique=True)
