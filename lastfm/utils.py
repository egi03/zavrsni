import requests
import hashlib
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.core.cache import cache
import logging
import time

logger = logging.getLogger(__name__)

LASTFM_API_BASE_URL = 'http://ws.audioscrobbler.com/2.0/'
LASTFM_API_KEY = getattr(settings, 'LASTFM_API_KEY', '')

class LastFMAPI:    
    def __init__(self):
        self.api_key = LASTFM_API_KEY
        self.base_url = LASTFM_API_BASE_URL
        
    def _make_request(self, method: str, params: Dict) -> Optional[Dict]:
        if not self.api_key:
            logger.error("Last.fm API key not configured")
            return None
            
        params['api_key'] = self.api_key
        params['format'] = 'json'
        params['method'] = method
        
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = requests.get(self.base_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'error' in data:
                        logger.error(f"Last.fm API error: {data.get('message', 'Unknown error')}")
                        return None
                    return data
                elif response.status_code == 429:
                    logger.warning(f"Rate limit hit, waiting {retry_delay}s")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Last.fm API request failed: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request exception on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
            except ValueError as e:
                logger.error(f"JSON decode error: {e}")
                return None
                
        return None
    
    def get_track_info(self, artist: str, track: str) -> Optional[Dict]:
        cache_key = f"lastfm_track_{hashlib.md5(f'{artist}_{track}'.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached:
            return cached
            
        params = {
            'artist': artist,
            'track': track,
            'autocorrect': '1'
        }
        
        data = self._make_request('track.getInfo', params)
        if data and 'track' in data:
            track_info = data['track']
            cache.set(cache_key, track_info, 86400)
            return track_info
        return None
    
    def get_track_tags(self, artist: str, track: str) -> List[Dict]:
        cache_key = f"lastfm_tags_{hashlib.md5(f'{artist}_{track}'.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached:
            return cached
            
        params = {
            'artist': artist,
            'track': track,
            'autocorrect': '1'
        }
        
        data = self._make_request('track.getTopTags', params)
        if data and 'toptags' in data:
            tags = data['toptags'].get('tag', [])
            if isinstance(tags, dict):
                tags = [tags]
            cache.set(cache_key, tags, 86400)
            return tags
        return []
    
    def get_similar_tracks(self, artist: str, track: str, limit: int = 20) -> List[Dict]:
        """Get similar tracks"""
        cache_key = f"lastfm_similar_{hashlib.md5(f'{artist}_{track}_{limit}'.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached:
            return cached
            
        params = {
            'artist': artist,
            'track': track,
            'limit': str(limit),
            'autocorrect': '1'
        }
        
        data = self._make_request('track.getSimilar', params)
        if data and 'similartracks' in data:
            tracks = data['similartracks'].get('track', [])
            if isinstance(tracks, dict):
                tracks = [tracks]
            cache.set(cache_key, tracks, 43200)
            return tracks
        return []
    
    def get_artist_tags(self, artist: str) -> List[Dict]:
        """Get top tags for an artist"""
        cache_key = f"lastfm_artist_tags_{hashlib.md5(artist.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached:
            return cached
            
        params = {
            'artist': artist,
            'autocorrect': '1'
        }
        
        data = self._make_request('artist.getTopTags', params)
        if data and 'toptags' in data:
            tags = data['toptags'].get('tag', [])
            if isinstance(tags, dict):
                tags = [tags]
            cache.set(cache_key, tags, 86400)
            return tags
        return []
    
    def get_tag_similar_tracks(self, tag: str, limit: int = 50) -> List[Dict]:
        """Get top tracks for a specific tag"""
        cache_key = f"lastfm_tag_tracks_{tag}_{limit}"
        cached = cache.get(cache_key)
        if cached:
            return cached
            
        params = {
            'tag': tag,
            'limit': str(limit)
        }
        
        data = self._make_request('tag.getTopTracks', params)
        if data and 'tracks' in data:
            tracks = data['tracks'].get('track', [])
            if isinstance(tracks, dict):
                tracks = [tracks]
            cache.set(cache_key, tracks, 21600)
            return tracks
        return []
    
    def search_track(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for tracks on Last.fm"""
        params = {
            'track': query,
            'limit': str(limit)
        }
        
        data = self._make_request('track.search', params)
        if data and 'results' in data:
            track_matches = data['results'].get('trackmatches', {})
            tracks = track_matches.get('track', [])
            if isinstance(tracks, dict):
                tracks = [tracks]
            return tracks
        return []

lastfm_api = LastFMAPI()

def get_track_tags_with_weights(artist: str, track: str) -> Dict[str, float]:
    """Get track tags with normalized weights"""
    tags = lastfm_api.get_track_tags(artist, track)
    
    tag_weights = {}
    max_count = 0
    
    for tag in tags[:10]:
        if isinstance(tag, dict) and 'name' in tag:
            count = int(tag.get('count', 0))
            if count > max_count:
                max_count = count
            tag_weights[tag['name'].lower()] = count
    
    if max_count > 0:
        for tag_name in tag_weights:
            tag_weights[tag_name] = tag_weights[tag_name] / max_count
    
    return tag_weights

def calculate_tag_similarity(tags1: Dict[str, float], tags2: Dict[str, float]) -> float:
    if not tags1 or not tags2:
        return 0.0
    
    common_tags = set(tags1.keys()) & set(tags2.keys())
    if not common_tags:
        return 0.0
    
    # Calculate weighted Jaccard similarity
    intersection_weight = sum(min(tags1[tag], tags2[tag]) for tag in common_tags)
    union_weight = sum(max(tags1.get(tag, 0), tags2.get(tag, 0)) 
                      for tag in set(tags1.keys()) | set(tags2.keys()))
    
    if union_weight == 0:
        return 0.0
    
    return intersection_weight / union_weight

def enrich_song_with_lastfm_data(song) -> bool:
    """Enrich a song object with Last.fm data"""
    try:
        track_info = lastfm_api.get_track_info(song.artist, song.name)
        if track_info:
            if 'playcount' in track_info:
                song.lastfm_playcount = int(track_info['playcount'])
            
            if 'listeners' in track_info:
                song.lastfm_listeners = int(track_info['listeners'])
        
        tags = get_track_tags_with_weights(song.artist, song.name)
        if tags:
            song.lastfm_tags = tags
            song.save()
            return True
            
    except Exception as e:
        logger.error(f"Error enriching song {song.id} with Last.fm data: {e}")
    
    return False

def batch_enrich_songs_with_lastfm(songs: List) -> int:
    enriched_count = 0
    
    for i, song in enumerate(songs):
        if i > 0 and i % 10 == 0:
            time.sleep(1)
        
        if enrich_song_with_lastfm_data(song):
            enriched_count += 1
            logger.info(f"Enriched song {song.id}: {song.name} by {song.artist}")
    
    return enriched_count