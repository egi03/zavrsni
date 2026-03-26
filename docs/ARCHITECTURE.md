# System Architecture

## App Layout

The project is a standard Django monolith split into six apps with clear responsibility boundaries.

```
accounts/        User authentication, registration, profiles
music/           Song and Playlist models, search, CRUD
recommendations/ ML engine — collaborative, content-based, hybrid
spotify/         Spotify OAuth flow, playlist import, API wrapper
lastfm/          Last.fm API wrapper, tag enrichment
social/          Follow system, messaging, activity feed, comments
```

Dependencies flow inward — `recommendations` depends on `music`, `lastfm`, and `spotify`, but none of those know about `recommendations`. `social` depends on `music` and `accounts` but nothing depends on `social`.

---

## Request Lifecycle

### Page request (playlist detail)

```
Browser GET /playlists/<id>/
  -> music.views.playlist_detail
     -> Playlist.objects.get(id)                    1 query
     -> playlist.songs.all()                        1 query
     -> get_playlist_recommendations(playlist)
          -> cache.get(cache_key)                   cache hit: return
          -> HybridRecommendation.objects            1 query (cache miss)
               .filter(playlist, strategy)
               .select_related('song')
               .order_by('-hybrid_score')[:8]
          -> cache.set(cache_key, ..., 1800)
     -> render playlist_detail.html
```

### AJAX recommendation refresh

```
Browser POST /playlists/<id>/recommendations/refresh/
  -> music.views.refresh_recommendations
     -> cache.delete(cache_key)
     -> HybridRecommender.update_hybrid_recommendations(playlist_id, strategy)
          -> recommend_hybrid()
               -> _get_candidate_songs()
                    -> PlaylistRecommender.recommend_for_playlist()   TF model
                    -> LastFMContentRecommender.recommend_by_tags()
                    -> LastFMContentRecommender.find_similar_by_lastfm_api()
                    -> popular fallback (if candidates < n_needed)
               -> get_collaborative_scores()
               -> get_content_tag_scores()
               -> get_content_similar_scores()
               -> get_popularity_scores()
               -> calculate_hybrid_score() x n_candidates
          -> HybridRecommendation.objects.bulk create
     -> get_playlist_recommendations()              fetch + cache
     -> JsonResponse({recommendations, strategy})
```

### Add song to playlist

```
Browser POST /playlists/<id>/add/   body: {song_id: spotify_id}
  -> music.views.add_to_playlist
     -> Song.objects.get(spotify_id=song_id)
     |  DoesNotExist:
     |    -> spotify.utils.get_track(song_id)          Spotify API
     |    -> spotify.utils.get_track_audio_features()  Spotify API (cached 1h)
     |    -> Song.objects.create(...)
     -> playlist.songs.add(song)
     -> cache.delete(recommendation cache keys)     invalidate stale recs
     -> JsonResponse({success, song_id, total_songs})
```

---

## Data Models

### Core

```
User (Django built-in)
  |
  +-- UserProfile         bio, profile_picture
  |
  +-- Playlist            name, is_public, description, spotify_id
        |
        +-- Song (M2M)    spotify_id, audio features, lastfm_tags (JSON)
```

### Recommendations

```
PlaylistRecommendation    precomputed collaborative filtering scores
HybridRecommendation      full per-strategy recommendation record
                          stores all component scores + explanation JSON
RecommendationFeedback    user actions on recommendations (added/skipped/liked)
```

### Social

```
UserFollow           follower -> following (User FK pair)
PlaylistFollow       user -> playlist
Activity             event log (playlist_created, song_added, user_followed, ...)
Notification         per-user alert (follow, message, comment, playlist_update)
Conversation         M2M of participants
Message              conversation FK, sender, content, shared_playlist/song
PlaylistComment      playlist FK, user FK, content, parent (self-FK for replies)
```

---

## Caching Strategy

All caching uses Django's default cache backend (local-memory in development).

| Key pattern | TTL | Invalidated on |
|-------------|-----|----------------|
| `playlist_recommendations_{id}_{strategy}` | 30 min | song added/removed, recommendation refresh |
| `recommendations_{id}_{strategy}` | 30 min | same |
| Spotify audio features | 1 hour | never (features don't change) |
| Last.fm track info/tags | 24 hours | never within a session |
| Last.fm similar tracks | 12 hours | never within a session |
| Recommendation stats | 5 min | automatic expiry |

Last.fm tag data on the `Song` model has a separate staleness check: if `lastfm_updated` is older than 30 days the content recommender triggers a re-enrichment on access.

---

## External API Integration

### Spotify

Two separate access patterns:

- **Client credentials** (`SpotifyClientManager`) — used for all song search and track metadata. No user login required. Token auto-refreshed after 55 minutes.
- **User OAuth** (`SpotifyAPI`) — only required for playlist import. Token stored in `SpotifyToken` model per user, refreshed transparently on expiry.

Retry strategy: 3 attempts, exponential backoff (1s, 2s, 4s). Client is reset on 401/403.

### Last.fm

Single `LastFMAPI` class with a module-level singleton (`lastfm_api`). All methods cache responses. Retry strategy matches Spotify (3 attempts, exponential backoff).

Tag enrichment is always called with `ensure_song_has_tags()` inside the content recommender — it enriches lazily on first recommendation request rather than at song creation time, so adding songs to a playlist stays fast.

---

## ML Model Persistence

The collaborative filtering model is saved with versioned timestamps:

```
media/
  recommendation_model/
    latest.txt              points to the most recent version directory
    20240315_142301/
      model.keras           TensorFlow SavedModel format
      encoders.pkl          playlist_encoder, song_encoder dicts
    20240316_091200/
      ...
```

`load_model()` reads `latest.txt` to find the current version. Legacy models saved directly in `recommendation_model/` are still loadable for backwards compatibility.

---

## Settings Reference

Key non-standard settings:

```python
RECOMMENDATION_SETTINGS = {
    'COLLABORATIVE_FACTORS': 50,   # embedding dimensions
    'DEFAULT_STRATEGY': 'balanced',
    'MAX_RECOMMENDATIONS': 50,
    'CACHE_TIMEOUT': 1800,         # seconds
    'BATCH_SIZE': 128,             # TF training batch
    'TRAINING_EPOCHS': 50,         # max epochs (EarlyStopping may stop earlier)
}
```

Required environment variables (see `.env.example`):

```
SECRET_KEY
DEBUG
SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET
LASTFM_API_KEY
```
