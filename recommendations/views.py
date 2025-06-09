from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.http import JsonResponse
from django.core.cache import cache
from music.models import Playlist, Song
from .models import HybridRecommendation, RecommendationFeedback
from .hybrid_recommender import HybridRecommender
from .serializers import (HybridRecommendationSerializer, RecommendationExplanationSerializer)
import logging

logger = logging.getLogger(__name__)


@login_required
def get_playlist_recommendations(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id)
    
    if playlist.user != request.user and not playlist.is_public:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    strategy = request.GET.get('strategy', 'balanced')
    refresh = request.GET.get('refresh', 'false').lower() == 'true'
    
    cache_key = f'recommendations_{playlist_id}_{strategy}'
    if not refresh:
        cached_data = cache.get(cache_key)
        if cached_data:
            return JsonResponse(cached_data)
    
    recommendations = HybridRecommendation.objects.filter(
        playlist=playlist,
        strategy=strategy
    ).select_related('song').order_by('-hybrid_score')[:20]
    
    if not recommendations or refresh:
        recommender = HybridRecommender()
        recommender.update_hybrid_recommendations(
            playlist_id, 
            strategy=strategy,
            n_recommendations=20
        )
        
        recommendations = HybridRecommendation.objects.filter(
            playlist=playlist,
            strategy=strategy
        ).select_related('song').order_by('-hybrid_score')[:20]
    
    serializer = HybridRecommendationSerializer(recommendations, many=True)
    data = {
        'recommendations': serializer.data,
        'strategy': strategy,
        'playlist_id': playlist_id
    }
    
    cache.set(cache_key, data, 1800)
    
    return JsonResponse(data)


@login_required
def get_recommendation_explanation(request, playlist_id, song_id):
    playlist = get_object_or_404(Playlist, id=playlist_id)
    song = get_object_or_404(Song, id=song_id)
    
    if playlist.user != request.user and not playlist.is_public:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    strategy = request.GET.get('strategy', 'balanced')
    
    try:
        recommendation = HybridRecommendation.objects.get(
            playlist=playlist,
            song=song,
            strategy=strategy
        )
    except HybridRecommendation.DoesNotExist:
        return JsonResponse({'error': 'Recommendation not found'}, status=404)
    
    similar_songs = _get_similar_songs_in_playlist(playlist, song)
    
    data = {
        'recommendation': HybridRecommendationSerializer(recommendation).data,
        'explanation': RecommendationExplanationSerializer({
            'scores': {
                'collaborative': recommendation.collaborative_score,
                'content_audio': recommendation.content_audio_score,
                'content_mood': recommendation.content_mood_score,
                'popularity': recommendation.popularity_score,
                'recency': recommendation.recency_score,
                'diversity': recommendation.diversity_score,
                'hybrid': recommendation.hybrid_score
            },
            'similar_songs': similar_songs,
            'strategy_info': recommendation.explanation
        }).data
    }
    
    return JsonResponse(data)


@login_required
def record_recommendation_feedback(request, recommendation_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    recommendation = get_object_or_404(HybridRecommendation, id=recommendation_id)
    
    if recommendation.playlist.user != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    action = request.POST.get('action')
    if action not in ['added', 'played', 'skipped', 'liked', 'disliked']:
        return JsonResponse({'error': 'Invalid action'}, status=400)
    
    feedback, created = RecommendationFeedback.objects.get_or_create(
        user=request.user,
        recommendation_id=recommendation_id,
        action=action
    )
    
    return JsonResponse({
        'success': True,
        'created': created,
        'action': action
    })


def _get_similar_songs_in_playlist(playlist, target_song):
    from .content_recommender import ContentBasedRecommender
    
    recommender = ContentBasedRecommender()
    target_features = recommender.get_song_features(target_song)
    
    if not target_features:
        return []
    
    similar_songs = []
    
    for song in playlist.songs.all():
        if song.id == target_song.id:
            continue
        
        song_features = recommender.get_song_features(song)
        if song_features:
            # Simple similarity calculation
            similarity = 0
            common_features = 0
            
            for feature in ['energy', 'valence', 'danceability', 'acousticness']:
                if feature in target_features and feature in song_features:
                    diff = abs(target_features[feature] - song_features[feature])
                    similarity += (1 - diff)
                    common_features += 1
            
            if common_features > 0:
                similarity = similarity / common_features
                if similarity > 0.7:
                    similar_songs.append({
                        'id': song.id,
                        'name': song.name,
                        'artist': song.artist,
                        'similarity': round(similarity, 2)
                    })
    
    return sorted(similar_songs, key=lambda x: x['similarity'], reverse=True)[:3]


@login_required
@cache_page(60 * 5)  # Cache for 5 minutes
def get_recommendation_stats(request):
    user = request.user
    
    stats = {
        'total_recommendations': HybridRecommendation.objects.filter(
            playlist__user=user
        ).count(),
        
        'feedback_stats': {
            'added': RecommendationFeedback.objects.filter(
                user=user, action='added'
            ).count(),
            'played': RecommendationFeedback.objects.filter(
                user=user, action='played'
            ).count(),
            'liked': RecommendationFeedback.objects.filter(
                user=user, action='liked'
            ).count(),
        },
        
        'strategy_usage': {},
        'recent_recommendations': []
    }
    
    for strategy in ['balanced', 'discovery', 'similarity', 'popular']:
        count = HybridRecommendation.objects.filter(
            playlist__user=user,
            strategy=strategy
        ).count()
        stats['strategy_usage'][strategy] = count
    
    recent = HybridRecommendation.objects.filter(
        playlist__user=user
    ).select_related('song', 'playlist').order_by('-created_at')[:10]
    
    stats['recent_recommendations'] = [
        {
            'song': rec.song.name,
            'artist': rec.song.artist,
            'playlist': rec.playlist.name,
            'score': rec.hybrid_score,
            'created_at': rec.created_at.isoformat()
        }
        for rec in recent
    ]
    
    return JsonResponse(stats)