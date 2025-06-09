from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class SpotifyToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    token_expires = models.DateTimeField()
    token_type = models.CharField(max_length=50)
    scope = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Spotify Token"
    
    def is_valid(self):
        return self.token_expires > timezone.now()
    
    def expires_in_seconds(self):
        if self.is_valid():
            return int((self.token_expires - timezone.now()).total_seconds())
        return 0
        
class SpotifyPlaylistImport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    spotify_playlist_id = models.CharField(max_length=100)
    local_playlist = models.ForeignKey('music.Playlist', on_delete=models.CASCADE)
    imported_at = models.DateTimeField(auto_now_add=True)
    last_synced = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'spotify_playlist_id']