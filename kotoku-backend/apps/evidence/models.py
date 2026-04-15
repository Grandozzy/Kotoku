from django.db import models


class Evidence(models.Model):
    checksum = models.CharField(max_length=128)
