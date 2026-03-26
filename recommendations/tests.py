"""
Unit tests for the recommendation engine.

Covers:
- PlaylistRecommender (collaborative filtering)
- LastFMContentRecommender (tag-based and API-based)
- HybridRecommender (score combination and strategy weighting)
"""

import os
from unittest.mock import MagicMock, patch

import numpy as np
import tensorflow as tf
from django.contrib.auth.models import User
from django.test import TestCase

from music.models import Playlist, Song
from recommendations.collaborative_recommender import PlaylistRecommender
from recommendations.content_recommender import LastFMContentRecommender
from recommendations.hybrid_recommender import HybridRecommender
from recommendations.models import HybridRecommendation, PlaylistRecommendation


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

def make_song(
    name="Test Song",
    artist="Test Artist",
    spotify_id=None,
    popularity=70,
    lastfm_listeners=None,
    lastfm_tags=None,
    energy=0.7,
    valence=0.5,
    danceability=0.6,
    acousticness=0.2,
):
    """Create and return a Song instance with sensible defaults."""
    return Song.objects.create(
        name=name,
        artist=artist,
        album="Test Album",
        year="2020",
        genre="Pop",
        photo="http://example.com/photo.jpg",
        spotify_id=spotify_id or f"spotify:track:{name.replace(' ', '')}",
        popularity=popularity,
        lastfm_listeners=lastfm_listeners,
        lastfm_tags=lastfm_tags or {},
        energy=energy,
        valence=valence,
        danceability=danceability,
        acousticness=acousticness,
    )


def make_user(username="testuser"):
    return User.objects.create_user(username=username, password="pass")


# ---------------------------------------------------------------------------
# Collaborative recommender tests
# ---------------------------------------------------------------------------

class TestPlaylistRecommender(TestCase):
    """Tests for the TensorFlow-backed collaborative filtering recommender."""

    def setUp(self):
        self.recommender = PlaylistRecommender(n_factors=4, n_epochs=3, batch_size=8)

        self.song1 = make_song("Song 1", "Artist 1", "sp_1")
        self.song2 = make_song("Song 2", "Artist 2", "sp_2")
        self.song3 = make_song("Song 3", "Artist 3", "sp_3")

        user1 = make_user("collab_user1")
        user2 = make_user("collab_user2")

        self.playlist1 = Playlist.objects.create(name="Playlist 1", user=user1)
        self.playlist1.songs.add(self.song1, self.song2)

        self.playlist2 = Playlist.objects.create(name="Playlist 2", user=user2)
        self.playlist2.songs.add(self.song2, self.song3)

    def test_prepare_data_returns_nonempty_arrays(self):
        playlist_indices, song_indices, ratings = self.recommender.prepare_data()

        self.assertGreater(len(playlist_indices), 0)
        self.assertGreater(len(song_indices), 0)
        self.assertEqual(len(playlist_indices), len(song_indices))
        self.assertEqual(len(ratings), len(playlist_indices))

    def test_prepare_data_encodes_playlists_and_songs(self):
        self.recommender.prepare_data()

        self.assertIn(self.playlist1.id, self.recommender.playlist_encoder)
        self.assertIn(self.song1.id, self.recommender.song_encoder)

    def test_prepare_data_ratings_are_all_one(self):
        _, _, ratings = self.recommender.prepare_data()
        self.assertTrue(np.all(ratings == 1.0))

    def test_build_model_returns_keras_model(self):
        n_playlists = 5
        n_songs = 10
        model = self.recommender.build_model(n_playlists, n_songs)

        self.assertIsInstance(model, tf.keras.Model)
        self.assertEqual(len(model.inputs), 2)
        self.assertEqual(model.output_shape, (None, 1))

    def test_build_model_embedding_dimension(self):
        model = self.recommender.build_model(5, 10)
        playlist_embedding = model.get_layer('playlist_embedding')
        self.assertEqual(playlist_embedding.output_dim, self.recommender.n_factors)

    def test_train_returns_history_with_loss(self):
        history = self.recommender.train()

        self.assertIsNotNone(history)
        self.assertIn('loss', history.history)
        self.assertIn('val_loss', history.history)

    def test_train_returns_none_when_no_data(self):
        # Empty the DB
        Song.objects.all().delete()
        Playlist.objects.all().delete()

        result = self.recommender.train()
        self.assertIsNone(result)

    def test_save_and_load_model(self):
        self.recommender.train()
        self.recommender.save_model()

        new_recommender = PlaylistRecommender()
        loaded = new_recommender.load_model()

        self.assertTrue(loaded)
        self.assertEqual(new_recommender.playlist_encoder, self.recommender.playlist_encoder)
        self.assertEqual(new_recommender.song_encoder, self.recommender.song_encoder)

    def test_recommend_for_playlist_returns_list(self):
        self.recommender.train()
        recs = self.recommender.recommend_for_playlist(self.playlist1.id, n_recommendations=2)

        self.assertIsInstance(recs, list)
        self.assertLessEqual(len(recs), 2)

    def test_recommend_for_playlist_excludes_existing_songs(self):
        self.recommender.train()
        recs = self.recommender.recommend_for_playlist(self.playlist1.id)
        existing_ids = set(self.playlist1.songs.values_list('id', flat=True))

        for song_id, _ in recs:
            self.assertNotIn(song_id, existing_ids)

    def test_recommend_for_playlist_scores_are_floats(self):
        self.recommender.train()
        recs = self.recommender.recommend_for_playlist(self.playlist1.id)

        for song_id, score in recs:
            self.assertIsInstance(song_id, int)
            self.assertIsInstance(score, float)

    def test_recommend_for_nonexistent_playlist_returns_empty(self):
        self.recommender.train()
        recs = self.recommender.recommend_for_playlist(99999)
        self.assertEqual(recs, [])

    def test_get_playlist_embedding_shape(self):
        self.recommender.train()
        embedding = self.recommender.get_playlist_embedding(self.playlist1.id)

        self.assertIsNotNone(embedding)
        self.assertEqual(embedding.shape, (self.recommender.n_factors,))

    def test_get_playlist_embedding_returns_none_for_unknown(self):
        self.recommender.train()
        embedding = self.recommender.get_playlist_embedding(99999)
        self.assertIsNone(embedding)

    def test_load_model_returns_false_when_no_saved_model(self):
        # Use a fresh instance pointing at a non-existent path
        fresh = PlaylistRecommender()
        fresh.model_path = "/tmp/does_not_exist_xyz"
        result = fresh.load_model()
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# Content recommender tests
# ---------------------------------------------------------------------------

class TestLastFMContentRecommender(TestCase):
    """Tests for tag-based and Last.fm API-based content recommender."""

    def setUp(self):
        self.recommender = LastFMContentRecommender()
        self.user = make_user("content_user")

        self.rock_song = make_song(
            "Rock Anthem", "Rock Band", "sp_rock",
            lastfm_tags={"rock": 0.9, "classic rock": 0.7, "guitar": 0.5},
        )
        self.pop_song = make_song(
            "Pop Hit", "Pop Star", "sp_pop",
            lastfm_tags={"pop": 0.9, "dance": 0.6},
        )
        self.rock_song2 = make_song(
            "Rock Song 2", "Rock Band 2", "sp_rock2",
            lastfm_tags={"rock": 0.8, "indie": 0.4},
        )

        self.playlist = Playlist.objects.create(name="Rock Playlist", user=self.user)
        self.playlist.songs.add(self.rock_song)

    def test_get_playlist_tag_profile_returns_dict(self):
        profile = self.recommender.get_playlist_tag_profile(self.playlist)
        self.assertIsInstance(profile, dict)
        self.assertGreater(len(profile), 0)

    def test_get_playlist_tag_profile_contains_known_tags(self):
        profile = self.recommender.get_playlist_tag_profile(self.playlist)
        self.assertIn("rock", profile)

    def test_get_playlist_tag_profile_empty_playlist_returns_empty(self):
        empty_playlist = Playlist.objects.create(name="Empty", user=self.user)
        profile = self.recommender.get_playlist_tag_profile(empty_playlist)
        self.assertEqual(profile, {})

    def test_get_playlist_tag_profile_normalized(self):
        profile = self.recommender.get_playlist_tag_profile(self.playlist)
        total = sum(profile.values())
        # Should be normalized (sum ≈ 1.0)
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_calculate_song_playlist_similarity_same_tags_high_score(self):
        profile = {"rock": 0.9, "classic rock": 0.7}
        similarity = self.recommender.calculate_song_playlist_similarity(
            self.rock_song, profile
        )
        self.assertGreater(similarity, 0.3)

    def test_calculate_song_playlist_similarity_no_matching_tags_returns_zero(self):
        profile = {"jazz": 0.9, "classical": 0.7}
        similarity = self.recommender.calculate_song_playlist_similarity(
            self.rock_song, profile
        )
        self.assertEqual(similarity, 0.0)

    def test_calculate_song_playlist_similarity_no_song_tags_returns_zero(self):
        song_without_tags = make_song("Bare Song", "Artist", "sp_bare")
        profile = {"rock": 0.9}
        similarity = self.recommender.calculate_song_playlist_similarity(
            song_without_tags, profile
        )
        self.assertEqual(similarity, 0.0)

    def test_calculate_song_playlist_similarity_score_in_range(self):
        profile = {"rock": 0.5}
        similarity = self.recommender.calculate_song_playlist_similarity(
            self.rock_song, profile
        )
        self.assertGreaterEqual(similarity, 0.0)
        self.assertLessEqual(similarity, 1.0)

    @patch('recommendations.content_recommender.enrich_song_with_lastfm_data')
    def test_recommend_by_tags_returns_list(self, mock_enrich):
        mock_enrich.return_value = True
        recs = self.recommender.recommend_by_tags(self.playlist, n_recommendations=5)
        self.assertIsInstance(recs, list)

    @patch('recommendations.content_recommender.enrich_song_with_lastfm_data')
    def test_recommend_by_tags_excludes_existing_songs(self, mock_enrich):
        mock_enrich.return_value = True
        recs = self.recommender.recommend_by_tags(self.playlist, n_recommendations=10)
        existing_ids = set(self.playlist.songs.values_list('id', flat=True))

        for song, _ in recs:
            self.assertNotIn(song.id, existing_ids)

    @patch('recommendations.content_recommender.enrich_song_with_lastfm_data')
    def test_recommend_by_tags_scores_in_range(self, mock_enrich):
        mock_enrich.return_value = True
        recs = self.recommender.recommend_by_tags(self.playlist, n_recommendations=10)

        for _, score in recs:
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.1)  # Slight boost allowed

    @patch('recommendations.content_recommender.enrich_song_with_lastfm_data')
    def test_recommend_by_tags_empty_playlist_returns_empty(self, mock_enrich):
        mock_enrich.return_value = False
        empty = Playlist.objects.create(name="Empty 2", user=self.user)
        recs = self.recommender.recommend_by_tags(empty)
        self.assertEqual(recs, [])

    @patch('recommendations.content_recommender.lastfm_api')
    def test_find_similar_by_lastfm_api_returns_list(self, mock_api):
        mock_api.get_similar_tracks.return_value = []
        recs = self.recommender.find_similar_by_lastfm_api(self.playlist)
        self.assertIsInstance(recs, list)

    @patch('recommendations.content_recommender.lastfm_api')
    def test_find_similar_by_lastfm_api_empty_playlist_returns_empty(self, mock_api):
        mock_api.get_similar_tracks.return_value = []
        empty = Playlist.objects.create(name="Empty 3", user=self.user)
        recs = self.recommender.find_similar_by_lastfm_api(empty)
        self.assertEqual(recs, [])

    @patch('recommendations.content_recommender.lastfm_api')
    def test_find_similar_by_lastfm_api_matches_database_songs(self, mock_api):
        mock_api.get_similar_tracks.return_value = [
            {
                'name': self.rock_song2.name,
                'artist': {'name': self.rock_song2.artist},
                'match': '0.9',
            }
        ]
        recs = self.recommender.find_similar_by_lastfm_api(self.playlist)
        song_ids = [s.id for s, _ in recs]
        self.assertIn(self.rock_song2.id, song_ids)

    @patch('recommendations.content_recommender.enrich_song_with_lastfm_data')
    def test_ensure_song_has_tags_returns_true_when_tags_exist(self, mock_enrich):
        result = self.recommender.ensure_song_has_tags(self.rock_song)
        self.assertTrue(result)
        mock_enrich.assert_not_called()

    @patch('recommendations.content_recommender.enrich_song_with_lastfm_data')
    def test_ensure_song_has_tags_calls_enrich_when_no_tags(self, mock_enrich):
        mock_enrich.return_value = True
        bare_song = make_song("No Tags", "Artist", "sp_notags")
        self.recommender.ensure_song_has_tags(bare_song)
        mock_enrich.assert_called_once_with(bare_song)


# ---------------------------------------------------------------------------
# Hybrid recommender tests
# ---------------------------------------------------------------------------

class TestHybridRecommender(TestCase):
    """Tests for the hybrid score combination and strategy weighting."""

    def setUp(self):
        self.user = make_user("hybrid_user")
        self.playlist = Playlist.objects.create(name="Hybrid Playlist", user=self.user)

        self.song = make_song(
            "Hybrid Song", "Artist", "sp_hybrid",
            popularity=80,
            lastfm_listeners=500000,
            lastfm_tags={"rock": 0.8},
        )
        self.playlist.songs.add(self.song)

    def test_strategies_have_weights_summing_to_one(self):
        recommender = HybridRecommender()
        for strategy, weights in recommender.strategies.items():
            total = sum(weights.values())
            self.assertAlmostEqual(total, 1.0, places=5, msg=f"Strategy '{strategy}' weights don't sum to 1")

    def test_strategies_all_present(self):
        recommender = HybridRecommender()
        for strategy in ('balanced', 'discovery', 'popular'):
            self.assertIn(strategy, recommender.strategies)

    def test_calculate_hybrid_score_balanced_strategy(self):
        recommender = HybridRecommender()
        components = {
            'collaborative': 0.8,
            'content_tags': 0.6,
            'content_similar': 0.5,
            'popularity': 0.4,
        }
        score = recommender.calculate_hybrid_score(self.playlist, self.song, components, 'balanced')
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_calculate_hybrid_score_unknown_strategy_falls_back_to_balanced(self):
        recommender = HybridRecommender()
        components = {
            'collaborative': 0.5,
            'content_tags': 0.5,
            'content_similar': 0.5,
            'popularity': 0.5,
        }
        score_unknown = recommender.calculate_hybrid_score(
            self.playlist, self.song, components, 'nonexistent'
        )
        score_balanced = recommender.calculate_hybrid_score(
            self.playlist, self.song, components, 'balanced'
        )
        self.assertAlmostEqual(score_unknown, score_balanced)

    def test_calculate_hybrid_score_popular_weights_popularity_more(self):
        recommender = HybridRecommender()
        high_pop_components = {
            'collaborative': 0.1,
            'content_tags': 0.1,
            'content_similar': 0.1,
            'popularity': 1.0,
        }
        low_pop_components = {
            'collaborative': 1.0,
            'content_tags': 0.1,
            'content_similar': 0.1,
            'popularity': 0.1,
        }
        score_pop = recommender.calculate_hybrid_score(
            self.playlist, self.song, high_pop_components, 'popular'
        )
        score_low = recommender.calculate_hybrid_score(
            self.playlist, self.song, low_pop_components, 'popular'
        )
        self.assertGreater(score_pop, score_low)

    def test_get_popularity_scores_normalizes_lastfm_listeners(self):
        recommender = HybridRecommender()
        candidate = make_song("Pop Song", "Artist", "sp_pop_score", popularity=50, lastfm_listeners=1000000)
        scores = recommender.get_popularity_scores([candidate])

        self.assertIn(candidate.id, scores)
        self.assertLessEqual(scores[candidate.id], 1.0)
        self.assertGreaterEqual(scores[candidate.id], 0.0)

    def test_get_popularity_scores_no_lastfm_uses_spotify(self):
        recommender = HybridRecommender()
        candidate = make_song("No LFM", "Artist", "sp_nolfm", popularity=60, lastfm_listeners=None)
        scores = recommender.get_popularity_scores([candidate])

        self.assertIn(candidate.id, scores)
        self.assertAlmostEqual(scores[candidate.id], 0.6, places=2)

    def test_get_popularity_scores_million_listeners_equals_one(self):
        recommender = HybridRecommender()
        candidate = make_song("Million", "Artist", "sp_million", popularity=50, lastfm_listeners=2000000)
        scores = recommender.get_popularity_scores([candidate])
        # 2M / 1M = 2.0 → clamped to 1.0 by min()
        self.assertLessEqual(scores[candidate.id], 1.0)

    @patch.object(HybridRecommender, '_get_candidate_songs')
    @patch.object(HybridRecommender, 'get_collaborative_scores')
    @patch.object(HybridRecommender, 'get_content_tag_scores')
    @patch.object(HybridRecommender, 'get_content_similar_scores')
    @patch.object(HybridRecommender, 'get_popularity_scores')
    def test_recommend_hybrid_returns_sorted_results(
        self, mock_pop, mock_similar, mock_tags, mock_collab, mock_candidates
    ):
        candidate = make_song("Cand1", "Artist", "sp_cand1")
        mock_candidates.return_value = [candidate]
        mock_collab.return_value = {candidate.id: 0.9}
        mock_tags.return_value = {candidate.id: 0.8}
        mock_similar.return_value = {candidate.id: 0.7}
        mock_pop.return_value = {candidate.id: 0.6}

        recommender = HybridRecommender()
        recs = recommender.recommend_hybrid(self.playlist, n_recommendations=5)

        self.assertIsInstance(recs, list)
        self.assertEqual(len(recs), 1)
        song, score, components = recs[0]
        self.assertEqual(song.id, candidate.id)
        self.assertGreater(score, 0.0)

    @patch.object(HybridRecommender, '_get_candidate_songs')
    def test_recommend_hybrid_returns_empty_when_no_candidates(self, mock_candidates):
        mock_candidates.return_value = []
        recommender = HybridRecommender()
        recs = recommender.recommend_hybrid(self.playlist)
        self.assertEqual(recs, [])

    @patch.object(HybridRecommender, 'recommend_hybrid')
    def test_update_hybrid_recommendations_creates_db_records(self, mock_recommend):
        candidate = make_song("DB Cand", "Artist", "sp_dbcand")
        components = {
            'collaborative': 0.5,
            'content_tags': 0.5,
            'content_similar': 0.5,
            'popularity': 0.5,
        }
        mock_recommend.return_value = [(candidate, 0.75, components)]

        recommender = HybridRecommender()
        recommender.update_hybrid_recommendations(self.playlist.id, strategy='balanced')

        saved = HybridRecommendation.objects.filter(
            playlist=self.playlist, song=candidate, strategy='balanced'
        )
        self.assertTrue(saved.exists())
        self.assertAlmostEqual(saved.first().hybrid_score, 0.75, places=2)

    def test_update_hybrid_recommendations_nonexistent_playlist_is_safe(self):
        recommender = HybridRecommender()
        # Should log error and return without raising
        recommender.update_hybrid_recommendations(99999)
