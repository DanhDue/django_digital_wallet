from django.db import models


class TokenModel(models.Model):
    address = models.CharField(max_length=255, blank=True)
    mintAuthority = models.CharField(max_length=255, blank=True)
    supply = models.CharField(max_length=255, blank=True)
    freezeAuthority = models.CharField(max_length=255, blank=True)
    decimals = models.IntegerField(default=0)
    isInitialized = models.BooleanField(default=False)
