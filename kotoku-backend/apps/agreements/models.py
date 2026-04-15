from django.db import models


class Agreement(models.Model):
    title = models.CharField(max_length=255)
