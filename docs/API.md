# API Reference

All JSON endpoints require the user to be logged in (session cookie). Unauthenticated requests are redirected to the login page except where noted.

Error responses always include an `error` string field. Success responses always include `"success": true`.

---

## Playlists

### List playlists
```
GET /playlists/
```
Returns the playlist list page (HTML). No JSON variant.

---

### Create playlist
```
POST /playlists/create/
Content-Type: application/x-www-form-urlencoded

name=My Playlist&description=Optional description&is_public=on
```
Redirects to playlist detail on success.

---

### Playlist detail
```
GET /playlists/<playlist_id>/
GET /playlists/<playlist_id>/?strategy=balanced
```
Returns the playlist detail page (HTML) with recommendations embedded if the playlist has 3 or more songs.

`strategy` — `balanced` (default) | `discovery` | `popular`

---

### Add song to playlist
```
POST /playlists/<playlist_id>/add/
Content-Type: application/json

{"song_id": "<spotify_track_id>"}
```

Creates the `Song` record if it does not already exist (fetches from Spotify API + enriches with Last.fm). Clears the recommendation cache for the playlist.

Response:
```json
{
  "success": true,
  "song_id": 42,
  "song_name": "Paranoid Android",
  "total_songs": 7
}
```

Errors: `400` song already in playlist, `404` track not found on Spotify, `500` internal error.

---

### Remove song from playlist
```
POST /playlists/<playlist_id>/remove/<song_id>/
```
Form POST (CSRF token required). Redirects back to playlist detail. Clears recommendation cache.

---

### Delete playlist
```
GET /playlists/<playlist_id>/delete/
```
Only the playlist owner can delete. Redirects to playlists list.

---

### Refresh recommendations
```
POST /playlists/<playlist_id>/recommendations/refresh/
Content-Type: application/json

{"strategy": "balanced"}
```

Clears the cache and regenerates recommendations by running the full hybrid pipeline. Can take several seconds on the first call.

Response:
```json
{
  "success": true,
  "strategy": "balanced",
  "recommendations": [
    {
      "song": {
        "id": 42,
        "name": "Paranoid Android",
        "artist": "Radiohead",
        "album": "OK Computer",
        "photo": "https://...",
        "spotify_id": "6LgJvl0Xdtc73RJ1mmpotq",
        "primary_tags": ["alternative rock", "art rock", "britpop"],
        "lastfm_listeners": 1200000
      },
      "score": 0.74,
      "explanation": {
        "collaborative": 0.61,
        "content_tags": 0.48,
        "content_similar": 0.30,
        "popularity": 0.82
      }
    }
  ]
}
```

---

### Add recommended song to playlist
```
POST /playlists/<playlist_id>/recommendations/add/
Content-Type: application/json

{"song_id": 42}
```

Adds the song (by internal DB id, not Spotify id) and logs a `RecommendationFeedback` record with `action=added`.

Response:
```json
{"success": true, "message": "Song added to playlist"}
```

---

### Search songs
```
GET /music/search/?query=radiohead
```

Searches Spotify. No authentication required.

Response — array of track objects:
```json
[
  {
    "id": "6LgJvl0Xdtc73RJ1mmpotq",
    "name": "Paranoid Android",
    "artist": "Radiohead",
    "album": "OK Computer",
    "year": "1997",
    "image": "https://..."
  }
]
```

Returns `[]` if query is shorter than 2 characters.

---

## Recommendations (standalone endpoints)

These endpoints are separate from the music app and used internally by the recommendations subsystem.

### Get recommendations for playlist
```
GET /recommendations/playlist/<playlist_id>/
GET /recommendations/playlist/<playlist_id>/?strategy=discovery&refresh=true
```

Returns cached recommendations or generates them if missing.

`refresh=true` — bypass cache and regenerate.

Response:
```json
{
  "playlist_id": 5,
  "strategy": "discovery",
  "recommendations": [ ... ]
}
```

---

### Get recommendation explanation
```
GET /recommendations/playlist/<playlist_id>/song/<song_id>/explanation/
GET /recommendations/playlist/<playlist_id>/song/<song_id>/explanation/?strategy=balanced
```

Returns the full explanation for a specific song recommendation.

Response:
```json
{
  "recommendation": {
    "id": 101,
    "hybrid_score": 0.74,
    "collaborative_score": 0.61,
    "content_audio_score": 0.48,
    "content_mood_score": 0.30,
    "popularity_score": 0.82,
    "strategy": "balanced"
  },
  "explanation": {
    "scores": {
      "collaborative": 0.61,
      "content_audio": 0.48,
      "content_mood": 0.30,
      "popularity": 0.82,
      "hybrid": 0.74
    },
    "similar_songs": [
      {"id": 10, "name": "Karma Police", "artist": "Radiohead", "similarity": 0.81}
    ],
    "strategy_info": {
      "components": {"collaborative": 0.61, "content_tags": 0.48},
      "strategy": "balanced",
      "timestamp": "2024-03-15T14:23:01Z",
      "primary_tags": ["alternative rock", "art rock"]
    }
  }
}
```

---

### Record recommendation feedback
```
POST /recommendations/feedback/<recommendation_id>/
Content-Type: application/x-www-form-urlencoded

action=added
```

`action` — `added` | `played` | `skipped` | `liked` | `disliked`

Only the playlist owner can record feedback.

Response:
```json
{"success": true, "created": true, "action": "added"}
```

---

### Recommendation stats
```
GET /recommendations/stats/
```

Returns aggregate recommendation stats for the logged-in user. Cached for 5 minutes.

Response:
```json
{
  "total_recommendations": 240,
  "feedback_stats": {
    "added": 18,
    "played": 5,
    "liked": 3
  },
  "strategy_usage": {
    "balanced": 120,
    "discovery": 80,
    "popular": 40
  },
  "recent_recommendations": [
    {
      "song": "Paranoid Android",
      "artist": "Radiohead",
      "playlist": "My Playlist",
      "score": 0.74,
      "created_at": "2024-03-15T14:23:01Z"
    }
  ]
}
```

---

## Social

### Activity feed
```
GET /social/feed/
GET /social/feed/?page=2
```
Returns HTML page. Activities from followed users, paginated at 20 per page.

---

### Follow / unfollow user
```
POST /social/follow/user/<username>/
```

Toggles follow state. Creates or deletes a `UserFollow` record and logs an `Activity`.

Response:
```json
{"success": true, "following": true, "followers_count": 14}
```

---

### Follow / unfollow playlist
```
POST /social/follow/playlist/<playlist_id>/
```

Toggles follow state for a public playlist.

Response:
```json
{"success": true, "following": true}
```

---

### Messages

#### List conversations
```
GET /social/messages/
```
HTML page listing all conversations.

#### View conversation
```
GET /social/messages/conversation/<conversation_id>/
```
HTML page with message thread. Marks messages as read.

#### Start conversation
```
GET /social/messages/start/<username>/
```
Creates a new conversation if one does not exist, then redirects to it.

#### Send message
```
POST /social/messages/send/
Content-Type: application/json

{
  "conversation_id": 3,
  "content": "Hey, great playlist!",
  "shared_playlist_id": null,
  "shared_song_id": null
}
```

Response:
```json
{
  "success": true,
  "message": {
    "id": 55,
    "content": "Hey, great playlist!",
    "sender": "alice",
    "created_at": "2024-03-15T14:23:01Z",
    "is_read": false
  }
}
```

#### Poll new messages
```
GET /social/messages/poll/<conversation_id>/?last_message_id=54
```

Long-poll endpoint used by the frontend to check for new messages. Returns only messages with `id > last_message_id`.

Response:
```json
{
  "success": true,
  "messages": [ ... ],
  "has_new": true
}
```

---

### Add comment to playlist
```
POST /social/playlist/<playlist_id>/comment/
Content-Type: application/json

{"content": "Great selection!"}
```

Playlist must be public or owned by the user.

Response:
```json
{
  "success": true,
  "comment": {
    "id": 12,
    "content": "Great selection!",
    "user": "alice",
    "created_at": "2024-03-15T14:23:01Z"
  }
}
```

---

### Notifications
```
GET /social/notifications/
```
HTML page. Marks all notifications as read on view.

---

## Accounts

### Register
```
POST /accounts/register/
Content-Type: application/x-www-form-urlencoded
```
Standard Django form POST. Redirects to home on success.

### Login
```
POST /accounts/login/
```
Accepts username or email. Redirects to `next` parameter or profile on success.

### Logout
```
GET /accounts/logout/
```
Clears session. Redirects to login page.

### Profile (own)
```
GET  /accounts/profile/
POST /accounts/profile/    (profile picture upload)
```

### Profile (other user)
```
GET /accounts/profile/<username>/
```
Public profile page with public playlists and follow button.

### Search profiles
```
GET /accounts/search-profiles/?q=alice
```

Returns matching users. Requires at least 2 characters.

Response:
```json
{
  "users": [
    {"username": "alice", "profile_picture": "/media/profile_pictures/alice.jpg"}
  ]
}
```

---

## Spotify Integration

### Connect Spotify account
```
GET /spotify/connect/
```
Redirects to Spotify OAuth authorization page.

### OAuth callback
```
GET /spotify/callback/?code=...&state=...
```
Exchanges authorization code for tokens and stores them. Redirects to import page.

### List importable playlists
```
GET /spotify/import/
```
HTML page listing the user's Spotify playlists.

### Import a playlist
```
GET /spotify/import/<spotify_playlist_id>/
```
Imports all tracks from the Spotify playlist, creating `Song` records as needed. Redirects to the new playlist detail page.

### Disconnect Spotify
```
POST /spotify/disconnect/
```
Deletes the stored `SpotifyToken` for the user.

### Check Spotify connection status
```
GET /spotify/status/
```

Response:
```json
{"connected": true, "spotify_user": "alice_spotify"}
```
