from django.db import models
from music.models import Song, Playlist, User

class PlaylistRecommendation(models.Model):
    """"Store precomputed scores, to not have to compute them every time."""
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='recommendations')
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    score = models.FloatField()
    reason = models.CharField(max_length=255, default='collaborative_filtering')
    recommendation_type = models.CharField(
        max_length=50,
        choices=[
            ('collaborative', 'Collaborative Filtering'),
            ('content', 'Content-Based'),
            ('hybrid', 'Hybrid'),
        ],
        default='hybrid'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['playlist', 'song', 'recommendation_type']
        ordering = ['-score', '-updated_at']
        indexes = [
            models.Index(fields=['playlist', '-score']),
            models.Index(fields=['updated_at']),
        ]
        
    def __str__(self):
        return f"{self.playlist.name} - {self.song.name} ({self.score:.2f})"
        
        
class HybridRecommendation(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='hybrid_recommendations')
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    
    hybrid_score = models.FloatField()
    
    collaborative_score = models.FloatField(default=0.0)
    content_audio_score = models.FloatField(default=0.0)
    content_mood_score = models.FloatField(default=0.0)
    popularity_score = models.FloatField(default=0.0)
    recency_score = models.FloatField(default=0.0)
    diversity_score = models.FloatField(default=0.0)
    
    strategy = models.CharField(
        max_length=50, 
        default='balanced',
        choices=[
            ('balanced', 'Balanced'),
            ('discovery', 'Discovery'),
            ('similarity', 'Similarity-focused'),
            ('popular', 'Popular'),
        ]
    )
    explanation = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['playlist', 'song', 'strategy']
        ordering = ['-hybrid_score']
        indexes = [
            models.Index(fields=['playlist', 'strategy','hybrid_score']),
            models.Index(fields=['updated_at']),
        ]
        verbose_name = 'Hybrid Recommendation'
        verbose_name_plural = 'Hybrid Recommendations'
        db_table = 'hybrid_recommendations'
    
    def __str__(self):
        return f"{self.playlist.name} - {self.song.name} (Hybrid: {self.hybrid_score:.2f})"
    

class RecommendationFeedback(models.Model):
    """Track user feedback on recommendations"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recommendation = models.ForeignKey(
        PlaylistRecommendation, 
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    action = models.CharField(
        max_length=20,
        choices=[
            ('added', 'Added to playlist'),
            ('played', 'Played'),
            ('skipped', 'Skipped'),
            ('liked', 'Liked'),
            ('disliked', 'Disliked'),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'recommendation', 'action']