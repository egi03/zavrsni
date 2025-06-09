import numpy as np
from typing import List, Dict, Tuple
from music.models import Song, Playlist
from django.core.cache import cache
import hashlib


def calculate_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors"""
    if vec1.size == 0 or vec2.size == 0:
        return 0.0
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def get_cache_key(prefix: str, *args) -> str:
    """Generate consistent cache key"""
    key_parts = [prefix] + [str(arg) for arg in args]
    key_string = '_'.join(key_parts)
    
    # Hash if too long
    if len(key_string) > 200:
        hash_obj = hashlib.md5(key_string.encode())
        return f"{prefix}_{hash_obj.hexdigest()}"
    
    return key_string


def batch_get_or_create_recommendations(
    playlist_id: int,
    song_scores: List[Tuple[int, float]],
    recommendation_type: str = 'hybrid'
) -> int:
    """Batch create recommendations"""
    from .models import PlaylistRecommendation
    
    PlaylistRecommendation.objects.filter(
        playlist_id=playlist_id,
        recommendation_type=recommendation_type
    ).delete()
    
    recommendations = [
        PlaylistRecommendation(
            playlist_id=playlist_id,
            song_id=song_id,
            score=score,
            recommendation_type=recommendation_type
        )
        for song_id, score in song_scores
    ]
    
    PlaylistRecommendation.objects.bulk_create(
        recommendations,
        ignore_conflicts=True
    )
    
    return len(recommendations)


def normalize_scores(scores: Dict[int, float]) -> Dict[int, float]:
    """Normalize scores to 0-1 range"""
    if not scores:
        return {}
    
    min_score = min(scores.values())
    max_score = max(scores.values())
    
    if max_score == min_score:
        return {k: 0.5 for k in scores.keys()}
    
    return {
        k: (v - min_score) / (max_score - min_score)
        for k, v in scores.items()
    }