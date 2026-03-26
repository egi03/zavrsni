"""
Unit tests for lastfm/utils.py.

All HTTP calls are mocked — no real Last.fm API calls are made.
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase

from lastfm.utils import (
    LastFMAPI,
    batch_enrich_songs_with_lastfm,
    calculate_tag_similarity,
    enrich_song_with_lastfm_data,
    get_track_tags_with_weights,
)
from music.models import Song


def make_song(name="Test Song", artist="Test Artist", spotify_id=None):
    return Song.objects.create(
        name=name,
        artist=artist,
        album="Album",
        year="2020",
        genre="Pop",
        photo="http://example.com/photo.jpg",
        spotify_id=spotify_id or f"sp_{name.replace(' ', '')}",
    )


# ---------------------------------------------------------------------------
# LastFMAPI tests
# ---------------------------------------------------------------------------

class TestLastFMAPIRequests(TestCase):
    """Tests for LastFMAPI._make_request and related methods."""

    def setUp(self):
        self.api = LastFMAPI()
        self.api.api_key = "test_api_key"

    @patch('lastfm.utils.requests.get')
    def test_make_request_returns_data_on_200(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'track': {'name': 'Test'}}
        mock_get.return_value = mock_response

        result = self.api._make_request('track.getInfo', {'artist': 'A', 'track': 'T'})
        self.assertEqual(result, {'track': {'name': 'Test'}})

    @patch('lastfm.utils.requests.get')
    def test_make_request_returns_none_on_api_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'error': 6, 'message': 'Track not found'}
        mock_get.return_value = mock_response

        result = self.api._make_request('track.getInfo', {'artist': 'A', 'track': 'T'})
        self.assertIsNone(result)

    @patch('lastfm.utils.requests.get')
    def test_make_request_returns_none_on_500(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = self.api._make_request('track.getInfo', {})
        self.assertIsNone(result)

    def test_make_request_returns_none_when_no_api_key(self):
        self.api.api_key = ""
        result = self.api._make_request('track.getInfo', {})
        self.assertIsNone(result)

    @patch('lastfm.utils.requests.get')
    def test_make_request_retries_on_request_exception(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = [
            req_lib.exceptions.RequestException("timeout"),
            req_lib.exceptions.RequestException("timeout"),
            req_lib.exceptions.RequestException("timeout"),
        ]
        result = self.api._make_request('track.getInfo', {})
        self.assertIsNone(result)
        self.assertEqual(mock_get.call_count, 3)


class TestLastFMAPIGetMethods(TestCase):
    """Tests for the high-level get_* methods with caching."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.api = LastFMAPI()
        self.api.api_key = "test_api_key"

    @patch.object(LastFMAPI, '_make_request')
    def test_get_track_info_returns_track_data(self, mock_request):
        mock_request.return_value = {
            'track': {'name': 'Bohemian Rhapsody', 'playcount': '1000000', 'listeners': '500000'}
        }
        result = self.api.get_track_info("Queen", "Bohemian Rhapsody")
        self.assertEqual(result['name'], 'Bohemian Rhapsody')

    @patch.object(LastFMAPI, '_make_request')
    def test_get_track_info_returns_none_when_not_found(self, mock_request):
        mock_request.return_value = None
        result = self.api.get_track_info("Unknown", "Unknown")
        self.assertIsNone(result)

    @patch.object(LastFMAPI, '_make_request')
    def test_get_track_tags_returns_list(self, mock_request):
        mock_request.return_value = {
            'toptags': {
                'tag': [
                    {'name': 'rock', 'count': '100'},
                    {'name': 'classic rock', 'count': '80'},
                ]
            }
        }
        tags = self.api.get_track_tags("Queen", "Bohemian Rhapsody")
        self.assertIsInstance(tags, list)
        self.assertEqual(len(tags), 2)

    @patch.object(LastFMAPI, '_make_request')
    def test_get_track_tags_handles_single_tag_dict(self, mock_request):
        """Last.fm returns a dict instead of list when there is only one tag."""
        mock_request.return_value = {
            'toptags': {'tag': {'name': 'rock', 'count': '100'}}
        }
        tags = self.api.get_track_tags("Artist", "Song")
        self.assertIsInstance(tags, list)
        self.assertEqual(len(tags), 1)

    @patch.object(LastFMAPI, '_make_request')
    def test_get_track_tags_returns_empty_on_error(self, mock_request):
        mock_request.return_value = None
        tags = self.api.get_track_tags("Artist", "Song")
        self.assertEqual(tags, [])

    @patch.object(LastFMAPI, '_make_request')
    def test_get_similar_tracks_returns_list(self, mock_request):
        mock_request.return_value = {
            'similartracks': {
                'track': [
                    {'name': 'We Will Rock You', 'artist': {'name': 'Queen'}, 'match': '0.9'},
                ]
            }
        }
        tracks = self.api.get_similar_tracks("Queen", "Bohemian Rhapsody")
        self.assertIsInstance(tracks, list)
        self.assertEqual(len(tracks), 1)

    @patch.object(LastFMAPI, '_make_request')
    def test_get_similar_tracks_returns_empty_on_error(self, mock_request):
        mock_request.return_value = None
        tracks = self.api.get_similar_tracks("Artist", "Song")
        self.assertEqual(tracks, [])


# ---------------------------------------------------------------------------
# Utility function tests
# ---------------------------------------------------------------------------

class TestGetTrackTagsWithWeights(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    @patch('lastfm.utils.lastfm_api')
    def test_returns_normalized_weights(self, mock_api):
        mock_api.get_track_tags.return_value = [
            {'name': 'rock', 'count': '100'},
            {'name': 'indie', 'count': '50'},
        ]
        weights = get_track_tags_with_weights("Artist", "Song")

        self.assertIn('rock', weights)
        self.assertAlmostEqual(weights['rock'], 1.0)
        self.assertAlmostEqual(weights['indie'], 0.5)

    @patch('lastfm.utils.lastfm_api')
    def test_returns_lowercase_tag_names(self, mock_api):
        mock_api.get_track_tags.return_value = [
            {'name': 'Classic Rock', 'count': '80'},
        ]
        weights = get_track_tags_with_weights("Artist", "Song")
        self.assertIn('classic rock', weights)
        self.assertNotIn('Classic Rock', weights)

    @patch('lastfm.utils.lastfm_api')
    def test_returns_empty_dict_when_no_tags(self, mock_api):
        mock_api.get_track_tags.return_value = []
        weights = get_track_tags_with_weights("Artist", "Song")
        self.assertEqual(weights, {})


class TestCalculateTagSimilarity(TestCase):

    def test_identical_tags_returns_one(self):
        tags = {"rock": 0.9, "indie": 0.5}
        similarity = calculate_tag_similarity(tags, tags)
        self.assertAlmostEqual(similarity, 1.0)

    def test_no_common_tags_returns_zero(self):
        tags1 = {"rock": 0.9}
        tags2 = {"jazz": 0.9}
        similarity = calculate_tag_similarity(tags1, tags2)
        self.assertEqual(similarity, 0.0)

    def test_partial_overlap_returns_between_zero_and_one(self):
        tags1 = {"rock": 0.9, "indie": 0.5}
        tags2 = {"rock": 0.7, "pop": 0.8}
        similarity = calculate_tag_similarity(tags1, tags2)
        self.assertGreater(similarity, 0.0)
        self.assertLess(similarity, 1.0)

    def test_empty_first_dict_returns_zero(self):
        similarity = calculate_tag_similarity({}, {"rock": 0.9})
        self.assertEqual(similarity, 0.0)

    def test_empty_second_dict_returns_zero(self):
        similarity = calculate_tag_similarity({"rock": 0.9}, {})
        self.assertEqual(similarity, 0.0)

    def test_similarity_is_symmetric(self):
        tags1 = {"rock": 0.8, "indie": 0.4}
        tags2 = {"rock": 0.6, "pop": 0.9}
        self.assertAlmostEqual(
            calculate_tag_similarity(tags1, tags2),
            calculate_tag_similarity(tags2, tags1),
        )


class TestEnrichSongWithLastfmData(TestCase):

    @patch('lastfm.utils.lastfm_api')
    @patch('lastfm.utils.get_track_tags_with_weights')
    def test_enriches_song_with_tags_and_listeners(self, mock_tags, mock_api):
        mock_api.get_track_info.return_value = {
            'playcount': '100000',
            'listeners': '50000',
        }
        mock_tags.return_value = {'rock': 0.9, 'indie': 0.5}

        song = make_song("Enrich Me", "Artist", "sp_enrich")
        result = enrich_song_with_lastfm_data(song)

        self.assertTrue(result)
        song.refresh_from_db()
        self.assertEqual(song.lastfm_listeners, 50000)
        self.assertEqual(song.lastfm_playcount, 100000)
        self.assertIn('rock', song.lastfm_tags)

    @patch('lastfm.utils.lastfm_api')
    @patch('lastfm.utils.get_track_tags_with_weights')
    def test_returns_false_when_no_tags(self, mock_tags, mock_api):
        mock_api.get_track_info.return_value = None
        mock_tags.return_value = {}

        song = make_song("No Tags", "Artist", "sp_notags")
        result = enrich_song_with_lastfm_data(song)
        self.assertFalse(result)

    @patch('lastfm.utils.lastfm_api')
    @patch('lastfm.utils.get_track_tags_with_weights')
    def test_returns_false_on_exception(self, mock_tags, mock_api):
        mock_api.get_track_info.side_effect = Exception("API error")
        mock_tags.return_value = {}

        song = make_song("Exception Song", "Artist", "sp_exc")
        result = enrich_song_with_lastfm_data(song)
        self.assertFalse(result)


class TestBatchEnrichSongsWithLastfm(TestCase):

    @patch('lastfm.utils.enrich_song_with_lastfm_data')
    def test_counts_enriched_songs(self, mock_enrich):
        mock_enrich.side_effect = [True, False, True]
        songs = [
            make_song("Song A", "Artist", "sp_a"),
            make_song("Song B", "Artist", "sp_b"),
            make_song("Song C", "Artist", "sp_c"),
        ]
        count = batch_enrich_songs_with_lastfm(songs)
        self.assertEqual(count, 2)

    @patch('lastfm.utils.enrich_song_with_lastfm_data')
    def test_empty_list_returns_zero(self, mock_enrich):
        count = batch_enrich_songs_with_lastfm([])
        self.assertEqual(count, 0)
        mock_enrich.assert_not_called()
