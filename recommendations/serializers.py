from rest_framework import serializers
from .models import HybridRecommendation
from music.models import Song


class SongSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = [
            'id', 'name', 'artist', 'album', 'year', 
            'spotify_id', 'preview_url', 'popularity'
        ]


class HybridRecommendationSerializer(serializers.ModelSerializer):
    song = SongSerializer(read_only=True)
    
    class Meta:
        model = HybridRecommendation
        fields = [
            'id', 'song', 'hybrid_score', 'collaborative_score',
            'content_audio_score', 'content_mood_score', 
            'popularity_score', 'recency_score', 'diversity_score',
            'strategy', 'created_at'
        ]


class RecommendationExplanationSerializer(serializers.Serializer):
    scores = serializers.DictField()
    similar_songs = serializers.ListField()
    strategy_info = serializers.DictField()