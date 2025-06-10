import numpy as np
from typing import List, Tuple, Dict, Optional
from django.db.models import Q, Count, Avg
from music.models import Song, Playlist
from .models import PlaylistRecommendation, HybridRecommendation
from .collaborative_recommender import PlaylistRecommender
from .content_recommender import LastFMContentRecommender
from datetime import datetime
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class HybridRecommender:
    def __init__(self):
        self.collaborative_recommender = PlaylistRecommender()
        self.content_recommender = LastFMContentRecommender()
        
        self.strategies = {
            'balanced' : {
                'collaborative': 0.4,
                'content_tags': 0.3,
                'content_similar': 0.2,
                'popularity': 0.1
            },
            'discovery': {
                'collaborative': 0.2,
                'content_tags': 0.5,
                'content_similar': 0.2,
                'popularity': 0.1
            },
            'popular':{
                'collaborative': 0.1,
                'content_tags': 0.2,
                'content_similar': 0.1,
                'popularity': 0.6
            }
        }
        
    def get_collaborative_scores(self, playlist_id: int, song_ids: List[int]) -> Dict[int, float]:
        """Get collaborative filtering scores for specified songs

        Args:
            playlist_id (int): The ID of the playlist.
            song_ids (List[int]): A list of song IDs to get scores for.

        Returns:
            Dict[int, float]: A dictionary mapping song IDs to their collaborative scores.
        """
        scores = {}
        
        recommendations = PlaylistRecommendation.objects.filter(
            playlist_id=playlist_id,
            song_id__in=song_ids,
            recommendation_type='collaborative'
        ).values('song_id', 'score')
        
        for rec in recommendations:
            scores[rec['song_id']] = rec['score']
            
        missing_ids = set(song_ids) - set(scores.keys())
        if missing_ids and self.collaborative_recommender.load_model():
            try:
                cf_scores = self.collaborative_recommender.recommend_for_playlist(
                    playlist_id=playlist_id,
                    n_recommendations=len(missing_ids) + 10,
                )
                for song_id, score in cf_scores:
                    if song_id in missing_ids:
                        scores[song_id] = score
            except Exception as e:
                logger.error(f"Error in collaborative filtering for playlist {playlist_id}: {e}")
        
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {sid: score / max_score for sid, score in scores.items()}
        
        return scores
    
 
    def get_content_tag_scores(self, playlist: Playlist, songs: List[Song]) -> Dict[int, float]:
        """
        Get Last.fm tag-based filtering scores for specified songs

        Args:
            playlist (Playlist): The playlist for which to get tag scores.
            songs (List[Song]): The list of songs to get scores for.

        Returns:
            Dict[int, float]: A dictionary mapping song IDs to their tag scores.
        """
        scores = {}
        
        tag_recommendations = self.content_recommender.recommend_by_tags(
            playlist=playlist,
            n_recommendations=len(songs) * 2
        )
        
        for song, score in tag_recommendations:
            if song.id in [s.id for s in songs]:
                scores[song.id] = score
                
        for song in songs:
            if song.id not in scores:
                scores[song.id] = 0.3
        
        return scores
    
    
    def get_content_similar_scores(self, playlist: Playlist, songs: List[Song]) -> Dict[int, float]:
        """
        Get Last.fm similarity scores 

        Args:
            playlist (Playlist): The playlist for which to get similariy scores.
            songs (List[Song]): The list of songs to get scores for.

        Returns:
            Dict[int, float]: A dictionary mapping song IDs to their similarity scores.
        """
        scores = {}
        
        mood_recommendations = self.content_recommender.find_similar_by_lastfm_api(
            playlist=playlist,
            n_recommendations=len(songs) * 2
        )
        
        for song, score in mood_recommendations:
            if song.id in [s.id for s in songs]:
                scores[song.id] = score
                
        for song in songs:
            if song.id not in scores:
                scores[song.id] = 0.3
                
        return scores
    
    
    def get_popularity_scores(self, songs: List[Song]) -> Dict[int, float]:
        """
        Get popularity scores based on Last.fm listeners and Spotify popularity

        Args:
            songs (List[Song]): The list of songs to get popularity scores for.

        Returns:
            Dict[int, float]: A dictionary mapping song IDs to their popularity scores.
        """
        scores = {}
        
        for song in songs:
            spotify_score = (song.popularity / 100) if song.popularity else 0.3
            
            if song.lastfm_listeners:
                lastfm_score = min(song.lastfm_listeners, 1000000, 1.0)
                scores[song.id] = (spotify_score * 0.5 + lastfm_score * 0.5)
            else:
                scores[song.id] = spotify_score
        
        return scores
    
    
    def calculate_hybrid_score(
        self, 
        playlist: Playlist, 
        song: Song, 
        component_scores: Dict[str, float], 
        strategy: str = 'balanced'
        ) -> float:
        """
        Calculate the final hybrid score for a song

        Args:
            playlist (Playlist): The playlist for which to calculate the score.
            song (Song): The song to score
            component_scores (Dict[str, float]): A dictionary of component scores.
            strategy (str): The strategy to use for combining scores. Defaults to 'balanced'.

        Returns:
            float: The final hybrid score for the song.
        """
        
        weights = self.strategies.get(strategy, self.strategies['balanced'])
        
        score = sum(
            component_scores.get(component, 0) * weight
            for component, weight in weights.items()
        )
        
        return min(1.0, score)
    
    
    def recommend_hybrid(
        self,
        playlist: Playlist,
        n_recommendations: int = 20,
        strategy: str = 'balanced',
    ) -> List[Tuple[Song, float, Dict[str, float]]]:
        """
        Generate hybrid recommendations for a playlist

        Args:
            playlist (Playlist): The playlist to generate recommendations for.
            n_recommendations (int, optional): The number of recommendations to generate. Defaults to 20.
            strategy (str, optional): The strategy to use for generating recommendations. Defaults to 'balanced'.

        Returns:
            List[Tuple[Song, float, Dict[str, float]]]: A list of recommended songs with their scores and component scores.
        """
        logger.info(f"Generating hybrid recommendations for playlist: {playlist.id}")
        
        # Get candidates
        existing_ids = set(playlist.songs.values_list('id', flat=True))
        candidates = self._get_candidate_songs(playlist, existing_ids, n_recommendations)
        
        if not candidates:
            logger.warning('No candidates found')
            return []
        
        song_ids = [song.id for song in candidates]

        collaborative_scores = self.get_collaborative_scores(playlist.id, song_ids)
        content_tag_scores = self.get_content_tag_scores(playlist, candidates)
        content_similar_scores = self.get_content_similar_scores(playlist, candidates)
        popularity_scores = self.get_popularity_scores(candidates)
        
        recommendations = []
        
        for song in candidates:
            component_scores = {
                'collaborative': collaborative_scores.get(song.id, 0.3),
                'content_tags': content_tag_scores.get(song.id, 0.3),
                'content_similar': content_similar_scores.get(song.id, 0.3),
                'popularity': popularity_scores.get(song.id, 0.3)
            }
        
            hybrid_score = self.calculate_hybrid_score(
                playlist, song, component_scores, strategy
            )

            recommendations.append((song, hybrid_score, component_scores))

        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations[:n_recommendations]
    
    
    def _get_candidate_songs(self, playlist: Playlist, existing_ids: set, n_needed: int) -> List[Song]:
        candidates = []
        added_ids = set()
        
        if self.collaborative_recommender.load_model():
            cf_recs = self.collaborative_recommender.recommend_for_playlist(
                playlist.id, n_recommendations=n_needed * 2
            )
            for song_id, _ in cf_recs[:n_needed]:
                if song_id not in existing_ids and song_id not in added_ids:
                    try:
                        song = Song.objects.get(id=song_id)
                        candidates.append(song)
                        added_ids.add(song_id)
                    except Song.DoesNotExist:
                        pass
        
        content_recs = self.content_recommender.recommend_by_tags(playlist, n_recommendations=n_needed)
        for song, _ in content_recs:
            if song.id not in existing_ids and song.id not in added_ids:
                candidates.append(song)
                added_ids.add(song.id)
        
        similar_recs = self.content_recommender.find_similar_by_lastfm_api(playlist, n_needed)
        for song, _ in similar_recs:
            if song.id not in existing_ids and song.id not in added_ids:
                candidates.append(song)
                added_ids.add(song.id)
        
        if len(candidates) < n_needed:
            popular_songs = Song.objects.filter(
                Q(popularity__gte=70) | Q(lastfm_listeners__gte=100000)
            ).exclude(
                id__in=existing_ids
            ).order_by('-popularity', '-lastfm_listeners')[:n_needed]
            for song in popular_songs:
                if song.id not in added_ids:
                    candidates.append(song)
                    added_ids.add(song.id)
        
        logger.info(f"Generated {len(candidates)} unique candidates")
        return candidates[:n_needed * 3]


    def update_hybrid_recommendations(
        self,
        playlist_id: int,
        strategy: str = 'balanced',
        n_recommendations: int = 20
    ):
        """
        Clear existing recommendations for the specified playlist and
        strategy, then generates and saves new hybrid recommendations.

    Args:
        playlist_id (int): The ID of the playlist to update.
        strategy (str, optional): Recommendation strategy, defaults to 'balanced'.
        n_recommendations (int, optional): Recommendations to generate, Defaults to 20.
    """
        try:
            playlist = Playlist.objects.get(id=playlist_id)
        except Playlist.DoesNotExist:
            logger.error(f"Playlist {playlist_id} not found")
            return
        
        HybridRecommendation.objects.filter(
            playlist_id=playlist_id,
            strategy=strategy
        ).delete()
        
        recommendations = self.recommend_hybrid(playlist, n_recommendations, strategy)
        
        for song, score, components in recommendations:
            HybridRecommendation.objects.create(
                playlist=playlist,
                song=song,
                hybrid_score=score,
                collaborative_score=components.get('collaborative', 0),
                content_audio_score=components.get('content_tags', 0),
                content_mood_score=components.get('content_similar', 0),
                popularity_score=components.get('popularity', 0),
                strategy=strategy,
                explanation={
                    'components': components,
                    'strategy': strategy,
                    'timestamp': timezone.now().isoformat(),
                    'primary_tags': song.top_tags[:3] if hasattr(song, 'top_tags') else []
                }
            )
        
        logger.info(f"Updated {len(recommendations)} recommendations for playlist {playlist_id}")