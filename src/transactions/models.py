from django.db import models


class TransactionModel(models.Model):
    sender = models.CharField(max_length=255, blank=True)
    receiver = models.CharField(max_length=255, blank=True)
    token = models.CharField(max_length=255, blank=True)
    symbol = models.CharField(max_length=255, blank=True)
    blockTime = models.DateTimeField(auto_now=True)
    amount = models.BigIntegerField(default=0)
    fee = models.BigIntegerField(default=0)
    signature = models.CharField(max_length=255, blank=True)
    direction = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=255, blank=True)
