from django.db import models


class Notification(models.Model):
    channel = models.CharField(max_length=32)
