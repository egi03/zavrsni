"""
Unit tests for spotify/utils.py.

All Spotipy calls are mocked — no real Spotify API calls are made.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from music.models import Song
from spotify.utils import (
    SpotifyClientManager,
    create_song_from_spotify_track,
    get_track_audio_features,
    search_songs,
)


# ---------------------------------------------------------------------------
# SpotifyClientManager tests
# ---------------------------------------------------------------------------

class TestSpotifyClientManager(TestCase):

    def test_singleton_returns_same_instance(self):
        mgr1 = SpotifyClientManager()
        mgr2 = SpotifyClientManager()
        self.assertIs(mgr1, mgr2)

    @patch('spotify.utils.SPOTIFY_CLIENT_ID', '')
    @patch('spotify.utils.SPOTIFY_CLIENT_SECRET', '')
    def test_get_client_returns_none_when_no_credentials(self):
        manager = SpotifyClientManager()
        manager._client = None
        manager._token_expires_at = None
        client = manager.get_client()
        self.assertIsNone(client)


# ---------------------------------------------------------------------------
# search_songs tests
# ---------------------------------------------------------------------------

class TestSearchSongs(TestCase):

    @patch('spotify.utils.get_spotify_client')
    def test_search_songs_returns_formatted_list(self, mock_get_client):
        mock_sp = MagicMock()
        mock_get_client.return_value = mock_sp
        mock_sp.search.return_value = {
            'tracks': {
                'items': [
                    {
                        'id': 'abc123',
                        'name': 'Test Track',
                        'artists': [{'name': 'Test Artist'}],
                        'album': {
                            'name': 'Test Album',
                            'release_date': '2021-01-01',
                            'images': [{'url': 'http://example.com/img.jpg'}],
                        },
                        'uri': 'spotify:track:abc123',
                        'preview_url': None,
                        'popularity': 75,
                    }
                ]
            }
        }

        results = search_songs("Test Track", limit=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Test Track')
        self.assertEqual(results[0]['artist'], 'Test Artist')
        self.assertEqual(results[0]['id'], 'abc123')
        self.assertEqual(results[0]['year'], '2021')

    @patch('spotify.utils.get_spotify_client')
    def test_search_songs_returns_empty_when_no_client(self, mock_get_client):
        mock_get_client.return_value = None
        results = search_songs("Test")
        self.assertEqual(results, [])

    @patch('spotify.utils.get_spotify_client')
    def test_search_songs_returns_empty_on_exception(self, mock_get_client):
        mock_sp = MagicMock()
        mock_get_client.return_value = mock_sp
        mock_sp.search.side_effect = Exception("API error")

        results = search_songs("Test")
        self.assertEqual(results, [])

    @patch('spotify.utils.get_spotify_client')
    def test_search_songs_handles_missing_album_image(self, mock_get_client):
        mock_sp = MagicMock()
        mock_get_client.return_value = mock_sp
        mock_sp.search.return_value = {
            'tracks': {
                'items': [
                    {
                        'id': 'xyz',
                        'name': 'Song',
                        'artists': [{'name': 'Artist'}],
                        'album': {
                            'name': 'Album',
                            'release_date': '2020',
                            'images': [],
                        },
                        'uri': 'spotify:track:xyz',
                    }
                ]
            }
        }
        results = search_songs("Song")
        self.assertIsNone(results[0]['album_image'])


# ---------------------------------------------------------------------------
# get_track_audio_features tests
# ---------------------------------------------------------------------------

class TestGetTrackAudioFeatures(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    @patch('spotify.utils.get_spotify_client')
    def test_returns_feature_dict(self, mock_get_client):
        mock_sp = MagicMock()
        mock_get_client.return_value = mock_sp
        expected = {
            'id': 'feat_test_001',
            'energy': 0.8,
            'valence': 0.6,
            'danceability': 0.7,
            'acousticness': 0.1,
        }
        mock_sp.audio_features.return_value = [expected]

        result = get_track_audio_features('feat_test_001')
        self.assertEqual(result['energy'], 0.8)

    @patch('spotify.utils.get_spotify_client')
    def test_returns_none_when_no_features_returned(self, mock_get_client):
        mock_sp = MagicMock()
        mock_get_client.return_value = mock_sp
        mock_sp.audio_features.return_value = [None]

        result = get_track_audio_features('feat_test_null')
        self.assertIsNone(result)

    def test_returns_none_for_empty_track_id(self):
        result = get_track_audio_features('')
        self.assertIsNone(result)

    @patch('spotify.utils.get_spotify_client')
    def test_returns_cached_result_on_second_call(self, mock_get_client):
        mock_sp = MagicMock()
        mock_get_client.return_value = mock_sp
        features = {'id': 'cache_test_unique', 'energy': 0.5}
        mock_sp.audio_features.return_value = [features]

        # First call populates cache
        get_track_audio_features('cache_test_unique')
        # Second call should use cache, not call API again
        get_track_audio_features('cache_test_unique')

        mock_sp.audio_features.assert_called_once()


# ---------------------------------------------------------------------------
# create_song_from_spotify_track tests
# ---------------------------------------------------------------------------

class TestCreateSongFromSpotifyTrack(TestCase):

    def _make_track_data(self, track_id='track001', popularity=60):
        return {
            'id': track_id,
            'name': 'Test Song',
            'artists': [{'name': 'Test Artist'}],
            'album': {
                'name': 'Test Album',
                'release_date': '2021-06-15',
                'images': [{'url': 'http://example.com/img.jpg'}],
            },
            'uri': f'spotify:track:{track_id}',
            'preview_url': 'http://example.com/preview.mp3',
            'duration_ms': 210000,
            'popularity': popularity,
        }

    @patch('lastfm.utils.enrich_song_with_lastfm_data')
    def test_creates_new_song(self, mock_enrich):
        mock_enrich.return_value = True
        track = self._make_track_data('new_song_001')

        song = create_song_from_spotify_track(track)

        self.assertIsNotNone(song)
        self.assertEqual(song.name, 'Test Song')
        self.assertEqual(song.artist, 'Test Artist')
        self.assertEqual(song.spotify_id, 'new_song_001')

    @patch('lastfm.utils.enrich_song_with_lastfm_data')
    def test_updates_existing_song(self, mock_enrich):
        mock_enrich.return_value = True
        track_id = 'existing_001'
        Song.objects.create(
            name='Old Name',
            artist='Old Artist',
            album='Old Album',
            year='2010',
            genre='Unknown',
            photo='',
            spotify_id=track_id,
        )
        track = self._make_track_data(track_id, popularity=90)

        song = create_song_from_spotify_track(track)

        self.assertEqual(song.popularity, 90)
        self.assertEqual(Song.objects.filter(spotify_id=track_id).count(), 1)

    def test_returns_none_when_no_track_id(self):
        result = create_song_from_spotify_track({})
        self.assertIsNone(result)

    @patch('lastfm.utils.enrich_song_with_lastfm_data')
    def test_handles_lastfm_enrich_exception_gracefully(self, mock_enrich):
        mock_enrich.side_effect = Exception("Last.fm error")
        track = self._make_track_data('exception_track')

        # Should not raise
        song = create_song_from_spotify_track(track)
        self.assertIsNotNone(song)

    @patch('lastfm.utils.enrich_song_with_lastfm_data')
    def test_sets_year_from_release_date(self, mock_enrich):
        mock_enrich.return_value = True
        track = self._make_track_data('year_test')

        song = create_song_from_spotify_track(track)
        self.assertEqual(song.year, '2021')
