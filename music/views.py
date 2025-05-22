from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from .models import Song, Playlist
from spotify.utils import get_track, get_track_audio_features, search_songs as spotify_search_songs

def homepage(request):
    return render(request, 'index.html')

@login_required
def playlists(request):
    user_playlists = Playlist.objects.filter(user=request.user)
    return render(request, 'music/playlists.html', {'playlists': user_playlists})

@login_required
def playlist_detail(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id)
    
    if playlist.user != request.user and not playlist.is_public:
        messages.error(request, 'You do not have permission to view this playlist.')
        return redirect('music:playlists')
    
    songs = playlist.songs.all()
    context = {
        'playlist': playlist,
        'songs': songs
    }
    return render(request, 'music/playlist_detail.html', context)

@login_required
def create_playlist(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description", "No description")
        is_public = request.POST.get("is_public") == "on"
        
        if name:
            playlist = Playlist.objects.create(
                name=name,
                user=request.user,
                description=description,
                is_public=is_public
            )
            messages.success(request, 'Playlist created successfully!')
            return redirect('music:playlist_detail', playlist_id=playlist.id)
        else:
            messages.error(request, 'Playlist name is required.')
    
    return render(request, 'music/create_playlist.html')

@login_required
def delete_playlist(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id)
    
    if playlist.user == request.user:
        playlist.delete()
        messages.success(request, 'Playlist deleted successfully!')
    else:
        messages.error(request, 'You do not have permission to delete this playlist.')
    
    return redirect('music:playlists')

@login_required
def add_to_playlist(request, playlist_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': "Invalid method"})
    
    playlist = get_object_or_404(Playlist, id=playlist_id)
    
    if playlist.user != request.user:
        return JsonResponse({"success": False, 'error': 'This is not your playlist'})
    
    try:
        data = json.loads(request.body)
        song_id = data.get('song_id')
        
        if not song_id:
            return JsonResponse({'success': False, 'error': "Invalid song id"})
        
        try:
            song = Song.objects.get(spotify_id=song_id)
        except Song.DoesNotExist:
            try:
                track = get_track(song_id)
                
                if not track:
                    return JsonResponse({'success': False, 'error': 'Invalid song'}, status=404)
                
                audio_features = None
                try:
                    audio_features = get_track_audio_features(song_id)
                except Exception as feature_error:
                    print(f"Error fetching audio features: {feature_error}")
                
                song = Song.objects.create(
                    name=track.get('name', 'Unknown name'),
                    artist=track.get('artist', 'Unknown Artist'),
                    album=track.get('album', 'Unknown Album'),
                    year=track.get('year', 'Unknown'),
                    genre='Unknown',
                    photo=track.get('album_image', ''),
                    spotify_id=track.get('id', song_id),
                    spotify_uri=track.get('uri', ''),
                    preview_url=track.get('preview_url', ''),
                    popularity=track.get('popularity', 0)
                )
                
                if audio_features:
                    song.tempo = audio_features.get('tempo', 0.0)
                    song.energy = audio_features.get('energy', 0.0)
                    song.danceability = audio_features.get('danceability', 0.0)
                    song.acousticness = audio_features.get('acousticness', 0.0)
                    song.instrumentalness = audio_features.get('instrumentalness', 0.0)
                    song.liveness = audio_features.get('liveness', 0.0)
                    song.valence = audio_features.get('valence', 0.0)
                    song.save()
            except Exception as track_error:
                print(f"Error fetching track: {track_error}")
                return JsonResponse({'success': False, 'error': 'Unknown song info'})
        
        if song in playlist.songs.all():
            return JsonResponse({'success': False, 'error': 'Song already in playlist'})
        
        playlist.songs.add(song)
        return JsonResponse({'success': True})
    
    except Exception as e:
        print("Error: ", str(e))
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def remove_from_playlist(request, playlist_id, song_id):
    playlist = get_object_or_404(Playlist, id=playlist_id)
    song = get_object_or_404(Song, id=song_id)
    
    if playlist.user != request.user:
        messages.error(request, 'Not your playlist')
        return redirect('music:playlist_detail', playlist_id=playlist_id)
    
    playlist.songs.remove(song)
    
    messages.success(request, 'Removed')
    return redirect('music:playlist_detail', playlist_id=playlist_id)

def search_songs(request):
    q = request.GET.get('query', '')
    
    if not q or len(q) < 2:
        return JsonResponse([], safe=False)
    
    results = spotify_search_songs(q, limit=5)
    return JsonResponse(results, safe=False)