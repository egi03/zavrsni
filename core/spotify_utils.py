import requests
import json
import base64
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = 'https://api.spotify.com/v1'

SPOTIFY_CLIENT_ID = getattr(settings, 'SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = getattr(settings, 'SPOTIFY_CLIENT_SECRET', '')

def get_spotify_client():
    clinet_credentials_manager = SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    )
    return spotipy.Spotify(client_credentials_manager=clinet_credentials_manager)

def search_songs(query, limit=5):
    sp = get_spotify_client()
    if not sp:
        return []
    
    results = sp.search(q=query, type="track", limit=limit)
    tracks = results["tracks"]["items"]
    print(tracks[0])
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
    
def get_track(track_id):
    sp = get_spotify_client()
    if not sp:
        return None
    
    try:
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
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_track_audio_features(track_id):
    sp = get_spotify_client()
    if not sp:
        return None
    
    try:
        features = sp.audio_features(track_id)
        if features and len(features) > 0 and features[0]:
            return features[0]
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None