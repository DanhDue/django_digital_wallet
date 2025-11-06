from django.db import models

from django.conf import settings

User = settings.AUTH_USER_MODEL  # "auth.User"


# Create your models here.
class WalletModel(models.Model):
    # user =
    user = models.ForeignKey(
        User, default=None, null=True, blank=True, on_delete=models.SET_NULL
    )
    deviceToken = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True, null=True)
    email_confirmed = models.BooleanField(default=False)
    privateKey = models.CharField(max_length=255, blank=True)
    bs58PrivateKey = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    mnemonics = models.CharField(max_length=255, blank=True)
    balance = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
