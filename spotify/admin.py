from django.contrib import admin
from .models import SpotifyToken

@admin.register(SpotifyToken)
class SpotifyTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_type', 'token_expires']
    search_fields = ['user__username']