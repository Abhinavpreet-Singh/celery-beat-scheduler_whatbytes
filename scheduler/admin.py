from django.contrib import admin

from .models import EmailPreference


@admin.register(EmailPreference)
class EmailPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'timezone', 'birthday', 'preferred_hour', 'wants_campaigns']
    list_filter = ['timezone', 'wants_campaigns']
