import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from django.db.models import Q, Count
from django.utils import timezone
from music.models import Song, Playlist
from spotify.utils import get_track_audio_features
from lastfm.utils import (
    lastfm_api, 
    get_track_tags_with_weights, 
    calculate_tag_similarity,
    enrich_song_with_lastfm_data,
    batch_enrich_songs_with_lastfm
)
import logging

logger = logging.getLogger(__name__)


class LastFMContentRecommender:
    
    def __init__(self):
        self.min_tag_weight = 0.3
        self.tag_boost_factors = {
            'rock': 1.2,
            'pop': 1.1,
            'electronic': 1.2,
            'indie': 1.3,
            'alternative': 1.2,
            'jazz': 1.3,
            'classical': 1.4,
            'metal': 1.3,
            'hip hop': 1.2,
            'folk': 1.3
        }
    
    def ensure_song_has_tags(self, song: Song) -> bool:
        if not song.lastfm_tags or (song.lastfm_updated and (timezone.now() - song.lastfm_updated).days > 30):
            return enrich_song_with_lastfm_data(song)
        return bool(song.lastfm_tags)
    
    def get_playlist_tag_profile(self, playlist: Playlist) -> Dict[str, float]:
        """Calculate aggregated tag profile for a playlist"""
        songs = list(playlist.songs.all())
        if not songs:
            return {}
        
        songs_with_tags = []
        for song in songs:
            if self.ensure_song_has_tags(song) and song.lastfm_tags:
                songs_with_tags.append(song)
        
        if not songs_with_tags:
            logger.warning(f"No songs with tags in playlist {playlist.id}")
            return {}
        
        tag_scores = defaultdict(float)
        tag_counts = defaultdict(int)
        
        for song in songs_with_tags:
            for tag, weight in song.lastfm_tags.items():
                if weight >= self.min_tag_weight:
                    tag_scores[tag] += weight
                    tag_counts[tag] += 1
        
        avg_tag_profile = {}
        for tag, total_score in tag_scores.items():
            avg_weight = total_score / len(songs_with_tags)
            
            frequency_boost = min(tag_counts[tag] / len(songs_with_tags), 1.0)
            avg_tag_profile[tag] = avg_weight * (0.7 + 0.3 * frequency_boost)
        
        total_weight = sum(avg_tag_profile.values())
        if total_weight > 0:
            avg_tag_profile = {tag: weight/total_weight 
                              for tag, weight in avg_tag_profile.items()}
        
        return dict(sorted(avg_tag_profile.items(), 
                          key=lambda x: x[1], reverse=True)[:20])
    
    def calculate_song_playlist_similarity(self, song: Song, playlist_profile: Dict[str, float]) -> float:
        if not song.lastfm_tags or not playlist_profile:
            return 0.0
        
        similarity = 0.0
        matched_tags = 0
        
        for tag, playlist_weight in playlist_profile.items():
            if tag in song.lastfm_tags:
                song_weight = song.lastfm_tags[tag]
                tag_similarity = min(song_weight, playlist_weight) / max(song_weight, playlist_weight)
                
                boost = self.tag_boost_factors.get(tag, 1.0)
                
                similarity += tag_similarity * playlist_weight * boost
                matched_tags += 1
        
        if matched_tags < 2:
            similarity *= 0.5
        
        return min(similarity, 1.0)
    
    def recommend_by_tags(self, playlist: Playlist, n_recommendations: int = 20) -> List[Tuple[Song, float]]:
        logger.info(f"Generating tag-based recommendations for playlist {playlist.id}")
        
        playlist_profile = self.get_playlist_tag_profile(playlist)
        if not playlist_profile:
            logger.warning(f"Could not generate tag profile for playlist {playlist.id}")
            return []
        
        logger.info(f"Playlist tag profile: {list(playlist_profile.items())[:5]}")
        
        existing_song_ids = set(playlist.songs.values_list('id', flat=True))
        existing_artists = set(playlist.songs.values_list('artist', flat=True))
        
        candidates = Song.objects.exclude(
            id__in=existing_song_ids
        ).exclude(
            lastfm_tags={}
        )[:2000]
        
        recommendations = []
        
        for song in candidates:
            if not self.ensure_song_has_tags(song):
                continue
                
            similarity = self.calculate_song_playlist_similarity(song, playlist_profile)
            
            if song.artist in existing_artists:
                similarity *= 1.15
            
            # Consider popularity (normalize to 0-1)
            if song.lastfm_listeners:
                popularity_score = min(song.lastfm_listeners / 1000000, 1.0)  # Normalize by 1M listeners
                # Blend similarity and popularity
                final_score = similarity * 0.8 + popularity_score * 0.2
            else:
                final_score = similarity * 0.9  # Slight penalty for unknown popularity
            
            if final_score > 0.3:  # Minimum threshold
                recommendations.append((song, final_score))
        
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:n_recommendations]
    
    def find_similar_by_lastfm_api(self, playlist: Playlist, n_recommendations: int = 20) -> List[Tuple[Song, float]]:
        songs = list(playlist.songs.all())
        if not songs:
            return []
        
        existing_song_ids = set(playlist.songs.values_list('id', flat=True))
        similar_tracks_data = defaultdict(float)
        
        for song in songs[:10]:
            similar_tracks = lastfm_api.get_similar_tracks(song.artist, song.name, limit=30)
            
            for i, similar in enumerate(similar_tracks):
                if not similar or not isinstance(similar, dict):
                    continue
                    
                artist = similar.get('artist', {}).get('name', '')
                track_name = similar.get('name', '')
                
                if not artist or not track_name:
                    continue
                
                # Score based on position (higher position = more similar)
                position_score = 1.0 - (i / len(similar_tracks))
                match_score = float(similar.get('match', 0))
                
                key = (artist.lower(), track_name.lower())
                similar_tracks_data[key] += position_score * match_score
        
        # Find these tracks in our database
        recommendations = []
        
        for (artist, track_name), score in similar_tracks_data.items():
            # Try to find the song in our database
            songs = Song.objects.filter(
                artist__iexact=artist,
                name__iexact=track_name
            ).exclude(id__in=existing_song_ids)
            
            if songs.exists():
                song = songs.first()
                # Normalize score
                normalized_score = min(score / len(songs), 1.0)
                recommendations.append((song, normalized_score))
        
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:n_recommendations]
    
    def get_diverse_recommendations(self, playlist: Playlist, n_recommendations: int = 20) -> List[Tuple[Song, float]]:
        """Combine tag-based and API-based recommendations for diversity"""
        # Get recommendations from both methods
        tag_recs = self.recommend_by_tags(playlist, n_recommendations)
        api_recs = self.find_similar_by_lastfm_api(playlist, n_recommendations)
        
        # Combine with weights
        combined = {}
        
        # Add tag-based recommendations
        for song, score in tag_recs:
            combined[song.id] = (song, score * 0.6)  # 60% weight for tag-based
        
        # Add or update with API-based recommendations  
        for song, score in api_recs:
            if song.id in combined:
                # Average the scores if song appears in both
                existing_song, existing_score = combined[song.id]
                combined[song.id] = (song, (existing_score + score * 0.4) / 2)
            else:
                combined[song.id] = (song, score * 0.4)  # 40% weight for API-based
        
        # Sort by combined score
        recommendations = list(combined.values())
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations[:n_recommendations]
    
    def explain_recommendation(self, song: Song, playlist: Playlist) -> Dict[str, any]:
        """Explain why a song was recommended"""
        playlist_profile = self.get_playlist_tag_profile(playlist)
        
        explanation = {
            'common_tags': [],
            'tag_similarity': 0.0,
            'artist_in_playlist': False,
            'similar_to_songs': []
        }
        
        # Find common tags
        if song.lastfm_tags and playlist_profile:
            for tag in song.lastfm_tags:
                if tag in playlist_profile:
                    explanation['common_tags'].append({
                        'tag': tag,
                        'song_weight': song.lastfm_tags[tag],
                        'playlist_weight': playlist_profile[tag]
                    })
            
            explanation['tag_similarity'] = self.calculate_song_playlist_similarity(
                song, playlist_profile
            )
        
        # Check if artist is in playlist
        playlist_artists = set(playlist.songs.values_list('artist', flat=True))
        explanation['artist_in_playlist'] = song.artist in playlist_artists
        
        # Find which songs in playlist are most similar
        playlist_songs = playlist.songs.all()
        for playlist_song in playlist_songs:
            if playlist_song.lastfm_tags:
                similarity = calculate_tag_similarity(
                    song.lastfm_tags or {},
                    playlist_song.lastfm_tags
                )
                if similarity > 0.5:
                    explanation['similar_to_songs'].append({
                        'song': f"{playlist_song.name} - {playlist_song.artist}",
                        'similarity': similarity
                    })
        
        explanation['similar_to_songs'].sort(
            key=lambda x: x['similarity'], 
            reverse=True
        )
        explanation['similar_to_songs'] = explanation['similar_to_songs'][:3]
        
        return explanation