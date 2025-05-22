from django.db import models
from datetime import timezone
from django.contrib.auth.models import User

class SpotifyToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    token_expires = models.DateTimeField()
    token_type = models.CharField(max_length=50)
    
    def __str__(self):
        return f"{self.user.username}'s Spotify Token"
    
    def is_valid(self):
        return self.token_expires > timezone.now()