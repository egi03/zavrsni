from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import json

from .models import SpotifyToken, SpotifyPlaylistImport
from .utils import SpotifyAPI
from music.models import Playlist, Song


@login_required  
def connect_spotify(request):
    spotify_api = SpotifyAPI()
    redirect_uri = request.build_absolute_uri(reverse('spotify:callback'))
    print(f"DEBUG: Redirect URI being sent to Spotify: {redirect_uri}")
    
    auth_url = spotify_api.get_auth_url(request)
    return redirect(auth_url)



@login_required
def spotify_callback(request):
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error:
        messages.error(request, f'Povezivanje sa Spotify nije uspjelo')
        return redirect('accounts:profile')
    
    if not code:
        messages.error(request, 'Autorizacijski kod nije primljen od Spotify')
        return redirect('accounts:profile')
    
    spotify_api = SpotifyAPI()
    redirect_uri = request.build_absolute_uri(reverse('spotify:callback'))
    token_data = spotify_api.exchange_code_for_token(code, redirect_uri)
    
    if not token_data:
        messages.error(request, 'Token nije primljen')
        return redirect('accounts:profile')
    
    expires_at = timezone.now() + timedelta(seconds=token_data['expires_in'])
    
    spotify_token, created = SpotifyToken.objects.update_or_create(
        user=request.user,
        defaults={
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'token_expires': expires_at,
            'token_type': token_data.get('token_type', 'Bearer'),
            'scope': token_data.get('scope', '')
        }
    )
    
    messages.success(request, 'Uspješno povezani sa Spotify računom!')
    return redirect('spotify:import_playlists')

@login_required
def import_playlists(request):
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if not spotify_token.is_valid():
            messages.error(request, 'Spotify token je istekao, ponovo se povežite')
            return redirect('spotify:connect')
    except SpotifyToken.DoesNotExist:
        messages.error(request, 'Povežite se sa svojim Spotify računom')
        return redirect('spotify:connect')
    
    spotify_api = SpotifyAPI(request.user)
    playlists = spotify_api.get_user_playlists()
    
    if not playlists:
        messages.error(request, 'Greška u dohvaćanju playlista')
        return redirect('accounts:profile')
    
    imported_playlists_ids = set(SpotifyPlaylistImport.objects.filter(user=request.user).values_list('spotify_playlist_id', flat=True))
    available_playlists = [pl for pl in playlists if pl['id'] not in imported_playlists_ids]
    
    context = {
        'playlists': available_playlists,
        'imported_count': len(imported_playlists_ids)
    }
    
    return render(request, 'spotify/import_playlists.html', context)
    
@login_required
def import_playlist(request, playlist_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Wrong method'})
    
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        if not spotify_token.is_valid():
            return JsonResponse({'success': False, 'error': 'Token expired'})
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Spotify not connected'})
    
    if SpotifyPlaylistImport.objects.filter(user=request.user, spotify_playlist_id=playlist_id).exists():
        return JsonResponse({'success': False, 'error': 'Playlist already imported'})
    
    spotify_api = SpotifyAPI(request.user)
    
    playlist_data = spotify_api._make_authenticated_request(f'playlists/{playlist_id}')
    if not playlist_data:
        return JsonResponse({'success': False, 'error': 'Error fetching playlist data'})
    
    local_playlist = Playlist.objects.create(
        name=f'{playlist_data['name']} (from Spotify)',
        user=request.user,
        description=playlist_data.get('description', ''),
        is_public=False,
        spotify_id=playlist_id,
        spotify_url=playlist_data['external_urls']['spotify']
    )
    
    tracks = spotify_api.get_playlist_tracks(playlist_id)
    n_imported = 0
    
    for track_tmp in tracks:
        track = track_tmp.get('track')
        if not track or track['type'] != 'track':
            continue # podcasts
    
        song, created = Song.objects.get_or_create(
            spotify_id=track['id'],
            defaults={
                'name': track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'year': track['album']['release_date'][:4] if track['album']['release_date'] else 'Unknown',
                'genre': 'Unknown',
                'photo': track['album']['images'][0]['url'] if track['album']['images'] else '',
                'spotify_uri': track['uri'],
                'preview_url': track.get('preview_url', ''),
                'duration_ms': track.get('duration_ms', 0),
                'popularity': track.get('popularity', 0)
            }
        )
        
        local_playlist.songs.add(song)
        n_imported += 1
        
        
    SpotifyPlaylistImport.objects.create(
        user=request.user,
        spotify_playlist_id=playlist_id,
        local_playlist=local_playlist
    )
    
    return JsonResponse({
        'success': True, 
        'message': f'Imported {n_imported} songs',
        'playlist_id': local_playlist.id
    })

@login_required
def disconnect_spotify(request):
    if request.method == 'POST':
        try:
            spotify_token = SpotifyToken.objects.get(user=request.user)
            spotify_token.delete()
            messages.success(request, 'Spotify račun uklonjen!')
        except SpotifyToken.DoesNotExist:
            messages.info(request, 'Spotify račun nije povezan')
    
    return redirect('accounts:profile')

@login_required
def spotify_status(request):
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        is_connected = spotify_token.is_valid()
        expires_in = spotify_token.expires_in_seconds() if is_connected else 0
        
        return JsonResponse({
            'connected': is_connected,
            'expires_in': expires_in
        })
    except SpotifyToken.DoesNotExist:
        return JsonResponse({'connected': False})