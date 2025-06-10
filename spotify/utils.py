import requests
import base64
from urllib.parse import urlencode
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from .models import SpotifyToken
import time

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException

import logging
logger = logging.getLogger(__name__)

SPOTIFY_CLIENT_ID = getattr(settings, 'SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = getattr(settings, 'SPOTIFY_CLIENT_SECRET', '')

class SpotifyClientManager:
    _instance = None
    _client = None
    _token_expires_at = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self):
        """Get Spotify client with automatic token refresh"""
        now = datetime.now()
        
        if (self._client is None or 
            self._token_expires_at is None or 
            now >= self._token_expires_at):
            
            self._create_new_client()
        
        return self._client
    
    def _create_new_client(self):
        """Create new Spotify client"""
        try:
            if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
                logger.error("Spotify credentials missing")
                self._client = None
                return
            
            logger.info("Creating Spotify client...")
            
            client_credentials_manager = SpotifyClientCredentials(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET
            )
            
            self._client = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            
            test_result = self._client.search(q="test", type="track", limit=1)
            logger.info("Spotify client created and tested successfully")
            
            self._token_expires_at = datetime.now() + timedelta(seconds=3300)
            
        except Exception as e:
            logger.error(f"Error creating Spotify client: {e}")
            self._client = None

spotify_manager = SpotifyClientManager()

def get_spotify_client():
    return spotify_manager.get_client()

def search_songs(query, limit=5):
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            sp = get_spotify_client()
            if not sp:
                logger.error("No Spotify client available")
                return []
            
            results = sp.search(q=query, type="track", limit=limit)
            tracks = results["tracks"]["items"]
            
            formatted_tracks = []
            for track in tracks:
                formatted_tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': ', '.join([artist['name'] for artist in track["artists"]]),
                    'album': track['album']['name'],
                    'year': track['album']['release_date'][:4] if track['album']['release_date'] else "Unknown",
                    'album_image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'uri': track['uri']
                })
            
            return formatted_tracks
            
        except SpotifyException as e:
            logger.warning(f"Spotify API error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
                if e.http_status in [401, 403]:
                    spotify_manager._client = None
            else:
                logger.error(f"Failed to search songs after {max_retries} attempts")
                return []
        except Exception as e:
            logger.error(f"Unexpected error searching songs: {e}")
            return []
    
    return []

def get_track(track_id):
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            sp = get_spotify_client()
            if not sp:
                logger.error("No Spotify client available")
                return None
            
            track = sp.track(track_id)
            
            return {
                'id': track['id'],
                'name': track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'year': track['album']['release_date'][:4] if track['album']['release_date'] else None,
                'album_image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'preview_url': track['preview_url'],
                'popularity': track['popularity'],
                'uri': track['uri']
            }
            
        except SpotifyException as e:
            logger.warning(f"Spotify API error getting track {track_id} on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
                if e.http_status in [401, 403]:
                    spotify_manager._client = None
            else:
                logger.error(f"Failed to get track {track_id} after {max_retries} attempts")
                return None
        except Exception as e:
            logger.error(f"Unexpected error getting track {track_id}: {e}")
            return None
    
    return None

def get_track_audio_features(track_id):
    if not track_id:
        logger.warning("No track_id provided")
        return None
    
    cache_key = f"audio_features_{track_id}"
    cached_features = cache.get(cache_key)
    if cached_features:
        return cached_features
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            sp = get_spotify_client()
            if not sp:
                logger.error("No Spotify client available for audio features")
                return None
            
            logger.info(f"Getting audio features for track: {track_id}")
            
            features = sp.audio_features([track_id])
            
            if features and len(features) > 0 and features[0] is not None:
                logger.info(f"Successfully retrieved audio features for: {track_id}")
                cache.set(cache_key, features[0], 3600)  # Cache for 1 hour
                return features[0]
            else:
                logger.warning(f"No audio features returned for track: {track_id}")
                return None
                
        except SpotifyException as e:
            logger.error(f"Spotify API error getting audio features for {track_id} on attempt {attempt + 1}: "
                        f"Status: {e.http_status}, Message: {e.msg}")
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
                if e.http_status in [401, 403]:
                    spotify_manager._client = None
            else:
                logger.error(f"Failed to get audio features for {track_id} after {max_retries} attempts")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error getting audio features for {track_id}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                return None
    
    return None

def get_multiple_track_audio_features(track_ids):
    if not track_ids:
        return {}
    
    batch_size = 100  # Spotify API limit
    all_features = {}
    
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i:i + batch_size]
        
        uncached_tracks = []
        for track_id in batch:
            cache_key = f"audio_features_{track_id}"
            cached = cache.get(cache_key)
            if cached:
                all_features[track_id] = cached
            else:
                uncached_tracks.append(track_id)
        
        if not uncached_tracks:
            continue
        
        # Get uncached features
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                sp = get_spotify_client()
                if not sp:
                    logger.error("No Spotify client available for batch audio features")
                    break
                
                features = sp.audio_features(uncached_tracks)
                
                for track_id, feature in zip(uncached_tracks, features):
                    if feature:
                        all_features[track_id] = feature
                        cache_key = f"audio_features_{track_id}"
                        cache.set(cache_key, feature, 3600)
                
                break
                
            except SpotifyException as e:
                logger.error(f"Batch audio features error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    if e.http_status in [401, 403]:
                        spotify_manager._client = None
            except Exception as e:
                logger.error(f"Unexpected error in batch audio features: {e}")
                break
    
    return all_features


def create_song_from_spotify_track(track_data, fetch_audio_features=False):
    """
    Create or update a Song object from Spotify track data
    
    Args:
        track_data: Spotify track data
        fetch_audio_features: Whether to fetch audio features (default False for recommendations)
    """
    from music.models import Song
    from lastfm.utils import enrich_song_with_lastfm_data
    
    track_id = track_data.get('id')
    if not track_id:
        return None
    
    song_data = {
        'name': track_data.get('name', 'Unknown'),
        'artist': ', '.join([artist['name'] for artist in track_data.get('artists', [])]),
        'album': track_data.get('album', {}).get('name', 'Unknown'),
        'year': track_data.get('album', {}).get('release_date', '')[:4] or 'Unknown',
        'genre': 'Unknown',  # Spotify doesn't provide genre in track data
        'photo': track_data.get('album', {}).get('images', [{}])[0].get('url', '') if track_data.get('album', {}).get('images') else '',
        'spotify_id': track_id,
        'spotify_uri': track_data.get('uri', ''),
        'preview_url': track_data.get('preview_url', ''),
        'duration_ms': track_data.get('duration_ms', 0),
        'popularity': track_data.get('popularity', 0)
    }
    
    song, created = Song.objects.update_or_create(
        spotify_id=track_id,
        defaults=song_data
    )
    
    if created or not song.lastfm_tags:
        try:
            enrich_song_with_lastfm_data(song)
        except Exception as e:
            logger.warning(f"Could not enrich song {song.id} with Last.fm data: {e}")
    
    return song

# OAuth helper
class SpotifyAPI:
    """ Spotify API wrapper for user auth and data access"""
    
    BASE_URL = 'https://api.spotify.com/v1'
    AUTH_URL = 'https://accounts.spotify.com/authorize'
    TOKEN_URL = 'https://accounts.spotify.com/api/token'
    
    def __init__(self, user=None):
        self.user = user
        self.access_token = None
        if user:
            self._load_user_token()
    
    def _load_user_token(self):
        try:
            spotify_token = SpotifyToken.objects.get(user=self.user)
            if not spotify_token.is_valid():
                self._refresh_token(spotify_token)
            self.access_token = spotify_token.access_token
        except SpotifyToken.DoesNotExist:
            self.access_token = None
    
    def get_auth_url(self, request):
        scope = [
            'playlist-read-private',
            'playlist-read-collaborative',
            'user-library-read',
            'user-read-private'
        ]
        
        params = {
            'client_id': settings.SPOTIFY_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': request.build_absolute_uri(reverse('spotify:callback')),
            'scope': ' '.join(scope),
            'show_dialog': 'true'
        }
        
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    def exchange_code_for_token(self, code, redirect_uri):
        auth_header = base64.b64encode(
            f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        response = requests.post(self.TOKEN_URL, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()
        return None
    
    def _refresh_token(self, spotify_token):
        auth_header = base64.b64encode(
            f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode()
        ).decode()
        
        headers = {
            'Authorization': f"Basic {auth_header}",
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': spotify_token.refresh_token
        }
        
        response = requests.post(self.TOKEN_URL, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            
            spotify_token.access_token = token_data['access_token']
            spotify_token.token_expires = timezone.now() + timedelta(seconds=token_data['expires_in'])
            if 'refresh_token' in token_data:
                spotify_token.refresh_token = token_data['refresh_token']
            spotify_token.save()
            self.access_token = spotify_token.access_token
    
    def _make_authenticated_request(self, endpoint, params=None):
        if not self.access_token:
            return None
        
        headers = {'Authorization': f'Bearer {self.access_token}'}
        url = f'{self.BASE_URL}/{endpoint.lstrip('/')}'
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            if self.user:
                spotify_token = SpotifyToken.objects.get(user=self.user)
                self._refresh_token(spotify_token)
                headers = {'Authorization': f'Bearer {self.access_token}'}
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    return response.json()
                
        return None
    
    def get_user_playlists(self):
        playlists = []
        offset = 0
        limit = 50
        
        while True:
            params = {'limit': limit, 'offset': offset}
            data = self._make_authenticated_request('me/playlists', params)
            
            if not data or 'items' not in data:
                break
            
            playlists.extend(data['items'])
            
            if len(data['items']) < limit:
                break
            offset += limit
        
        return playlists
    
    def get_playlist_tracks(self, playlist_id):
        tracks = []
        offset = 0
        limit = 100
        
        while True:
            params = {'limit': limit, 'offset': offset}
            data = self._make_authenticated_request(f"playlists/{playlist_id}/tracks", params)
            
            if not data or 'items' not in data:
                break
            
            tracks.extend(data['items'])
            
            if len(data['items']) < limit:
                break
            offset += limit
            
        return tracks