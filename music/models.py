from django.db import models
from django.contrib.auth.models import User

class Song(models.Model):
    name = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    album = models.CharField(max_length=200)
    year = models.CharField(max_length=4)
    genre = models.CharField(max_length=100)
    photo = models.URLField(max_length=500)
    
    spotify_id = models.CharField(max_length=100, unique=True)
    spotify_uri = models.CharField(max_length=200, blank=True, null=True)
    preview_url = models.URLField(max_length=500, blank=True, null=True)
    duration_ms = models.IntegerField(blank=True, null=True)
    popularity = models.IntegerField(blank=True, null=True)
    
    # Audio features from Spotify API
    tempo = models.FloatField(blank=True, null=True)
    energy = models.FloatField(blank=True, null=True)
    danceability = models.FloatField(blank=True, null=True)
    acousticness = models.FloatField(blank=True, null=True)
    instrumentalness = models.FloatField(blank=True, null=True)
    liveness = models.FloatField(blank=True, null=True)
    valence = models.FloatField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.artist}"
    
class Playlist(models.Model):
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playlists')
    songs = models.ManyToManyField(Song, blank=True, related_name='playlists')
    is_public = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    spotify_id = models.CharField(max_length=100, blank=True, null=True)
    spotify_url = models.URLField(max_length=500, blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    class Meta:
        ordering = ['-created_at']