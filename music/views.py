from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.cache import cache
import json
from .models import Song, Playlist
from spotify.utils import get_track, get_track_audio_features, search_songs as spotify_search_songs

try:
    from recommendations.hybrid_recommender import HybridRecommender
    from recommendations.models import HybridRecommendation
    RECOMMENDATIONS_AVAILABLE = True
except ImportError:
    RECOMMENDATIONS_AVAILABLE = False

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
    recommendations = []
    has_enough_songs_for_recommendations = songs.count() >= 3
    
    if (RECOMMENDATIONS_AVAILABLE and 
        request.user == playlist.user and 
        has_enough_songs_for_recommendations):
        strategy = request.GET.get('strategy', 'balanced')
        recommendations = get_playlist_recommendations(playlist, strategy)
    
    context = {
    'playlist': playlist,
    'songs': songs,
    'recommendations': recommendations,
    'recommendations_available': RECOMMENDATIONS_AVAILABLE,
    'has_enough_songs_for_recommendations': has_enough_songs_for_recommendations,
    'current_strategy': request.GET.get('strategy', 'balanced')
}
    return render(request, 'music/playlist_detail.html', context)

def get_playlist_recommendations(playlist, strategy='balanced', limit=8):
    """Get recommendations for a playlist with caching"""
    cache_key = f'playlist_recommendations_{playlist.id}_{strategy}'
    cached_recs = cache.get(cache_key)
    
    if cached_recs:
        return cached_recs
    
    try:
        existing_recs = HybridRecommendation.objects.filter(
            playlist=playlist,
            strategy=strategy
        ).select_related('song').order_by('-hybrid_score')[:limit]
        
        if existing_recs.exists():
            recommendations = []
            for rec in existing_recs:
                
                primary_tags = []
                if rec.song.lastfm_tags:
                    sorted_tags = sorted(rec.song.lastfm_tags.items(), key=lambda x: x[1], reverse=True)[:3]
                    primary_tags = [tag[0] for tag in sorted_tags]
                
                recommendations.append({
                    'song': {
                        'id': rec.song.id,
                        'name': rec.song.name,
                        'artist': rec.song.artist,
                        'album': rec.song.album,
                        'photo': rec.song.photo,
                        'spotify_id': rec.song.spotify_id,
                        'year': rec.song.year,
                        'popularity': rec.song.popularity,
                        'primary_tags': primary_tags,
                        'lastfm_listeners': rec.song.lastfm_listeners,
                    },
                    'score': rec.hybrid_score,
                    'explanation': {
                        'collaborative': rec.collaborative_score,
                        'content_tags': rec.content_audio_score,
                        'content_similar': rec.content_mood_score,
                        'popularity': rec.popularity_score,
                    }
                })
            
            # Cache for 30 minutes
            cache.set(cache_key, recommendations, 1800)
            return recommendations
        
        return []
            
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return []



@login_required
def refresh_recommendations(request, playlist_id):
    """AJAX endpoint to refresh recommendations with detailed debugging"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    playlist = get_object_or_404(Playlist, id=playlist_id)
    
    if playlist.user != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if not RECOMMENDATIONS_AVAILABLE:
        return JsonResponse({'error': 'Recommendations not available'}, status=503)
    
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        data = json.loads(request.body) if request.body else {}
        strategy = data.get('strategy', 'balanced')
        
        logger.info(f"Starting recommendation generation for playlist {playlist_id}, strategy: {strategy}")
        
        cache_key = f'playlist_recommendations_{playlist.id}_{strategy}'
        cache.delete(cache_key)
        
        song_count = playlist.songs.count()
        logger.info(f"Playlist has {song_count} songs")
        
        if song_count == 0:
            return JsonResponse({
                'success': True,
                'recommendations': [],
                'strategy': strategy,
                'message': 'No songs in playlist'
            })
        

        logger.info("Creating HybridRecommender instance")
        recommender = HybridRecommender()
        
        logger.info("Calling update_hybrid_recommendations")
        recommender.update_hybrid_recommendations(
            playlist.id, 
            strategy=strategy, 
            n_recommendations=8
        )
        logger.info("Recommendations generated successfully")
            

        recommendations = get_playlist_recommendations(playlist, strategy)
        logger.info(f"Retrieved {len(recommendations)} recommendations")
        
        return JsonResponse({
            'success': True,
            'recommendations': recommendations,
            'strategy': strategy
        })
            
        
    except Exception as e:
        import traceback
        logger.error(f"Critical error in refresh_recommendations: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return JsonResponse({
            'error': f'Server error: {str(e)}',
            'debug_info': str(e)
        }, status=500)


@login_required
def add_recommended_song(request, playlist_id):
    """AJAX endpoint to add a recommended song to playlist"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    playlist = get_object_or_404(Playlist, id=playlist_id)
    
    if playlist.user != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        song_id = data.get('song_id')
        
        if not song_id:
            return JsonResponse({'error': 'Song ID required'}, status=400)
        
        song = get_object_or_404(Song, id=song_id)
        
        if song in playlist.songs.all():
            return JsonResponse({'error': 'Song already in playlist'}, status=400)
        
        playlist.songs.add(song)
        
        # Clear recommendations cache to refresh after adding
        for strategy in ['balanced', 'discovery', 'popular']:
            cache_key = f'playlist_recommendations_{playlist.id}_{strategy}'
            cache.delete(cache_key)
        
        return JsonResponse({'success': True, 'message': 'Song added to playlist'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
        
        # Clear recommendations cache
        for strategy in ['balanced', 'discovery', 'popular']:
            cache_key = f'playlist_recommendations_{playlist.id}_{strategy}'
            cache.delete(cache_key)
        
        return JsonResponse({
            'success': True,
            'song_id': song.id,  
            'song_name': song.name,  
            'total_songs': playlist.songs.count() 
        })
    
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
    
    # Clear recommendations cache
    for strategy in ['balanced', 'discovery', 'popular']:
        cache_key = f'playlist_recommendations_{playlist.id}_{strategy}'
        cache.delete(cache_key)
    
    messages.success(request, 'Removed')
    return redirect('music:playlist_detail', playlist_id=playlist_id)

def search_songs(request):
    q = request.GET.get('query', '')
    
    if not q or len(q) < 2:
        return JsonResponse([], safe=False)
    
    results = spotify_search_songs(q, limit=5)
    return JsonResponse(results, safe=False)