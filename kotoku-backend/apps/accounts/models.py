from django.db import models


class Account(models.Model):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.email
