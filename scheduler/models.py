import zoneinfo

from django.contrib.auth.models import User
from django.db import models

TIMEZONES = sorted(zoneinfo.available_timezones())


class EmailPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_preference')
    email = models.EmailField()
    timezone = models.CharField(max_length=64, choices=[(t, t) for t in TIMEZONES], default='Asia/Kolkata')
    birthday = models.DateField(null=True, blank=True)
    anniversary = models.DateField(null=True, blank=True)
    preferred_hour = models.PositiveSmallIntegerField(default=9)
    wants_campaigns = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.user.username} ({self.timezone})'
