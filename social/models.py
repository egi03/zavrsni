from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from music.models import Playlist, Song

class UserFollow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['follower', 'following']
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

class PlaylistFollow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followed_playlists')
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='playlist_followers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'playlist']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} follows {self.playlist.name}"

class Activity(models.Model):
    ACTIVITY_TYPES = [
        ('playlist_created', 'Created Playlist'),
        ('playlist_followed', 'Followed Playlist'),
        ('song_added', 'Added Song'),
        ('user_followed', 'Followed User'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    song = models.ForeignKey(Song, on_delete=models.CASCADE, null=True, blank=True)
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='activity_mentions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
        ]
        
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.playlist}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('follow', 'New Follower'),
        ('playlist_follow', 'Playlist Followed'),
        ('message', 'New Message'),
        ('comment', 'Playlist Commented'),
        ('playlist_update', 'Playlist Updated'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"Notification for {self.recipient.username}"

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def get_other_participant(self, user):
        return self.participants.exclude(id=user.id).first()
    
    def get_last_message(self):
        return self.messages.first()
    
    def __str__(self):
        return f"Conversation {self.id}"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    shared_playlist = models.ForeignKey(Playlist, on_delete=models.SET_NULL, null=True, blank=True)
    shared_song = models.ForeignKey(Song, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.conversation.updated_at = timezone.now()
        self.conversation.save()
    
    def __str__(self):
        return f"Message from {self.sender.username}"

class PlaylistComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playlist_comments')
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment {self.content} on {self.playlist.name}"
