from django.db import models


class Dispute(models.Model):
    reason = models.TextField()
