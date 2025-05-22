from django.contrib import admin
from .models import Song, Playlist

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ['name', 'artist', 'album', 'year']
    search_fields = ['name', 'artist', 'album']

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name', 'user__username']