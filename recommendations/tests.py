import unittest
import numpy as np
import tensorflow as tf
from django.test import TestCase
from recommendations.models import PlaylistRecommendation
from music.models import Playlist, Song
from recommendations.colaborative_recommender import PlaylistRecommender
from django.conf import settings
import os
from accounts.models import User

class TestPlaylistRecommender(TestCase):
    def setUp(self):
        """Set up test data and recommender instance."""
        self.recommender = PlaylistRecommender(n_factors=10, n_epochs=5, batch_size=32)
        
        self.song1 = Song.objects.create(
            name="Song 1",
            artist="Artist 1",
            album="Album 1",
            year="2020",
            genre="Pop",
            photo="http://example.com/photo1.jpg",
            spotify_id="spotify:track:1",  
            duration_ms=200000,
            popularity=75
        )
        self.song2 = Song.objects.create(
            name="Song 2",
            artist="Artist 2",
            album="Album 2",
            year="2021",
            genre="Rock",
            photo="http://example.com/photo2.jpg",
            spotify_id="spotify:track:2", 
            duration_ms=180000,
            popularity=80
        )
        self.song3 = Song.objects.create(
            name="Song 3",
            artist="Artist 3",
            album="Album 3",
            year="2022",
            genre="Jazz",
            photo="http://example.com/photo3.jpg",
            spotify_id="spotify:track:3",
            duration_ms=220000,
            popularity=70
        )
        
        self.playlist1 = Playlist.objects.create(name="Playlist 1", user=User.objects.create(username="testuser1"))
        self.playlist1.songs.add(self.song1, self.song2)
        
        self.playlist2 = Playlist.objects.create(name="Playlist 2", user=User.objects.create(username="testuser2"))
        self.playlist2.songs.add(self.song2, self.song3)

    def test_prepare_data(self):
        """Test data preparation."""
        playlist_indices, song_indices, ratings = self.recommender.prepare_data()
        
        self.assertGreater(len(playlist_indices), 0, "No playlists in data")
        self.assertGreater(len(song_indices), 0, "No songs in data")
        self.assertEqual(len(playlist_indices), len(song_indices), "Mismatch in indices length")
        self.assertEqual(len(ratings), len(playlist_indices), "Mismatch in ratings length")
        
        self.assertIn(self.playlist1.id, self.recommender.playlist_encoder, "Playlist not encoded")
        self.assertIn(self.song1.id, self.recommender.song_encoder, "Song not encoded")
        
        self.assertTrue(np.all(ratings == 1.0), "Ratings should be 1.0 for interactions")

    def test_build_model(self):
        """Test model building."""
        n_playlists = len(Playlist.objects.all())
        n_songs = len(Song.objects.all())
        model = self.recommender.build_model(n_playlists, n_songs)
        
        self.assertIsInstance(model, tf.keras.Model, "Model is not a Keras model")
        self.assertEqual(len(model.inputs), 2, "Model should have two inputs")
        self.assertEqual(model.output_shape, (None, 1), "Model output shape incorrect")
        
        playlist_embedding = model.get_layer('playlist_embedding')
        self.assertEqual(playlist_embedding.output_dim, self.recommender.n_factors, "Incorrect embedding size")

    def test_train(self):
        """Test model training."""
        history = self.recommender.train()
        
        self.assertIsNotNone(history, "Training failed, history is None")
        self.assertIn('loss', history.history, "Loss not recorded in history")
        self.assertIn('val_loss', history.history, "Validation loss not recorded")
        
        self.assertLess(history.history['loss'][-1], history.history['loss'][0], "Loss did not decrease")

    def test_save_load_model(self):
        """Test saving and loading the model."""
        self.recommender.train()
        self.recommender.save_model()
        
        self.assertTrue(os.path.exists(os.path.join(self.recommender.model_path, 'model.keras')), "Model not saved")
        self.assertTrue(os.path.exists(os.path.join(self.recommender.model_path, 'encoders.pkl')), "Encoders not saved")
        
        new_recommender = PlaylistRecommender()
        success = new_recommender.load_model()
        self.assertTrue(success, "Failed to load model")
        
        self.assertEqual(new_recommender.playlist_encoder, self.recommender.playlist_encoder, "Playlist encoder mismatch")

    def test_recommend_for_playlist(self):
        """Test recommendation generation."""
        self.recommender.train()  
        
        recommendations = self.recommender.recommend_for_playlist(self.playlist1.id, n_recommendations=2)
        
        self.assertIsInstance(recommendations, list, "Recommendations should be a list")
        self.assertLessEqual(len(recommendations), 2, "Too many recommendations returned")
        
        for song_id, score in recommendations:
            self.assertIsInstance(song_id, int, "Song ID should be an integer")
            self.assertIsInstance(score, float, "Score should be a float")
            
            playlist_songs = set(self.playlist1.songs.values_list('id', flat=True))
            self.assertNotIn(song_id, playlist_songs, "Recommended song already in playlist")

    def test_recommend_for_invalid_playlist(self):
        """Test recommendation for non-existent playlist."""
        self.recommender.train()
        recommendations = self.recommender.recommend_for_playlist(9999)  # Non-existent ID
        self.assertEqual(recommendations, [], "Should return empty list for invalid playlist")

    def test_get_playlist_embedding(self):
        """Test playlist embedding retrieval."""
        self.recommender.train()
        embedding = self.recommender.get_playlist_embedding(self.playlist1.id)
        
        self.assertIsNotNone(embedding, "Embedding should not be None")
        self.assertEqual(embedding.shape, (self.recommender.n_factors,), "Incorrect embedding shape")
        
        embedding = self.recommender.get_playlist_embedding(9999)
        self.assertIsNone(embedding, "Embedding should be None for invalid playlist")

if __name__ == '__main__':
    unittest.main()