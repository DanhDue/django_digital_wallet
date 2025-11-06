from django.db import models


class MarketModel(models.Model):
    name = models.CharField(max_length=255, blank=True)
    symbol = models.CharField(max_length=255, blank=True)
    slug = models.CharField(max_length=255, blank=True)
    rank = models.IntegerField(default=0)
    price = models.BigIntegerField(default=0)
    marketcap = models.BigIntegerField(default=0)
    volume24h = models.BigIntegerField(default=0)
    percentChange24h = models.BigIntegerField(default=0)
    percentChange7d = models.BigIntegerField(default=0)
    lastUpdated = models.DateTimeField(auto_now=True)
    logo = models.CharField(max_length=255, blank=True)
