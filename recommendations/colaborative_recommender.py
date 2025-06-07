import tensorflow as tf
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from django.db.models import Count
from recommendations.models import PlaylistRecommendation
import pickle
import os
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone
from music.models import Playlist, Song

class PlaylistRecommender:
    def __init__(self, n_factors=50, learning_rate=0.001, n_epochs=50, batch_size=128):
        """
        Initialize the PlaylistRecommender with hyperparameters for the model.

        Args:
            n_factors (int, optional): Number of latent factors. Defaults to 50.
            learning_rate (float, optional): How fast model learns. Defaults to 0.001.
            n_epochs (int, optional): How many times run trough data. Defaults to 50.
            batch_size (int, optional): Number of examples in 1 iteration. Defaults to 128.
        """
        self.n_factors = n_factors
        self.learning_rate = learning_rate
        self.n_epochs = n_epochs
        self.batch_size = batch_size
        self.model = None
        self.playlist_encoder = {}  # {playlist_id: index}
        self.song_encoder = {}      # {song_id: index}
        self.playlist_decoder = {}  # {index: playlist_id}
        self.song_decoder = {}      # {index: song_id}
        self.model_path = os.path.join(settings.MEDIA_ROOT, 'recommendation_model')
        os.makedirs(self.model_path, exist_ok=True)
        
        
    def prepare_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare playlist-song interaction matrix for training.

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray]: Tuple containing:
                - playlist indices: Array of playlist indices.
                - song indices: Array of song indices.
                - ratings: Array of interaction scores (1 for interaction, 0 otherwise).
        """
        
        playlists = Playlist.objects.filter(songs__isnull=False).distinct()
        
        interactions = []
        for playlist in playlists:
            for song in playlist.songs.all():
                interactions.append({
                    'playlist_id': playlist.id,
                    'song_id': song.id,
                    'rating': 1.0  # Implicit feedback: interaction exists
                })
        
        df = pd.DataFrame(interactions)
        
        # Create encoders for playlists and songs
        unique_playlists = df['playlist_id'].unique()
        unique_songs = df['song_id'].unique()
        
        self.playlist_encoder = {pid: idx for idx, pid in enumerate(unique_playlists)}
        self.song_encoder = {sid: idx for idx, sid in enumerate(unique_songs)}
        self.playlist_decoder = {idx: pid for pid, idx in self.playlist_encoder.items()}
        self.song_decoder = {idx: int(sid) for sid, idx in self.song_encoder.items()}

        # Encode the data
        playlist_indices = df['playlist_id'].map(self.playlist_encoder).values
        song_indices = df['song_id'].map(self.song_encoder).values
        ratings = df['rating'].values
        
        return playlist_indices, song_indices, ratings
    
    
    def build_model(self, n_playlists: int, n_songs: int) -> tf.keras.Model:
        """
        Build the matrix factorization model

        Args:
            n_playlists (int): Number of unique playlists
            n_songs (int): Number of unique songs

        Returns:
            tf.keras.Model: Compiled Keras model
        """
        
        playlist_input = tf.keras.layers.Input(shape=(1,), name='playlist_input') # Every playlist is represented by a single index
        song_input = tf.keras.layers.Input(shape=(1,), name='song_input')
        
        playlist_embedding = tf.keras.layers.Embedding(input_dim=n_playlists, output_dim=self.n_factors, 
                                                       name='playlist_embedding', embeddings_regularizer=tf.keras.regularizers.l2(1e-5)
                                                       )(playlist_input)
        song_embedding = tf.keras.layers.Embedding(input_dim=n_songs, output_dim=self.n_factors,
                                                   name='song_embedding', embeddings_regularizer=tf.keras.regularizers.l2(1e-5)
                                                   )(song_input)
        
        playlist_vec = tf.keras.layers.Flatten(name='playlist_flatten')(playlist_embedding)
        songs_vec = tf.keras.layers.Flatten(name='song_flatten')(song_embedding)
        

        # Calculate dot product and add biases
        dot_product = tf.keras.layers.Dot(axes=1, name='dot_product')([playlist_vec, songs_vec])
        
        playlist_bias = tf.keras.layers.Embedding(input_dim=n_playlists, output_dim=1, 
                                                  name='playlist_bias')(playlist_input)
        song_bias = tf.keras.layers.Embedding(input_dim=n_songs, output_dim=1, 
                                              name='song_bias')(song_input)
        
        playlist_bias = tf.keras.layers.Flatten()(playlist_bias)
        song_bias = tf.keras.layers.Flatten()(song_bias)
        
        output = tf.keras.layers.Add(name='output')([dot_product, playlist_bias, song_bias])
        
        
        model = tf.keras.Model(inputs=[playlist_input, song_input],
                               outputs=output, name='PlaylistRecommender')
        
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss='mean_squared_error',
            metrics=['mae']
        )
        
        return model
    
    
    def train(self):
        """
        Train the recommendation model on playlist-song interactions
        
        Returns:
            Training history if successful, None if failed
        """
        print("Preparing data ")
        playlist_indices, song_indices, ratings = self.prepare_data()
        
        if len(playlist_indices) == 0 or len(song_indices) == 0:
            print("No data")
            return None
        
        n_playlists = len(self.playlist_encoder)
        n_songs = len(self.song_encoder)
        print(f"Data prepared. Number of playlists: {n_playlists}\nNumber of songs:, {n_songs}")
        
        self.model = self.build_model(n_playlists, n_songs)
        
        history = self.model.fit(
            [playlist_indices, song_indices],
            ratings,
            batch_size=self.batch_size,
            epochs=self.n_epochs,
            validation_split=0.1,
            verbose=1
        )
        
        self.save_model()
        
        return history
        
        
    def save_model(self):
        self.model.save(os.path.join(self.model_path, 'model.keras'))
        
        with open(os.path.join(self.model_path, 'encoders.pkl'), 'wb') as f:
            pickle.dump({
                'playlist_encoder': self.playlist_encoder,
                'song_encoder': self.song_encoder,
                'playlist_decoder': self.playlist_decoder,
                'song_decoder': self.song_decoder
            }, f)
    
    
    def load_model(self):
        """
        Load the model and encoders from disk.
        
        Returns:
            True if loading successful, False if not
        """
        try:
            self.model = tf.keras.models.load_model(os.path.join(self.model_path, 'model.keras'))
            with open(os.path.join(self.model_path, 'encoders.pkl'), 'rb') as f:
                encoders = pickle.load(f)
                self.playlist_encoder = encoders['playlist_encoder']
                self.song_encoder = encoders['song_encoder']
                self.playlist_decoder = encoders['playlist_decoder']
                self.song_decoder = encoders['song_decoder']
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    
    def get_playlist_embedding(self, playlist_id: int) -> Optional[np.ndarray]:
        """
        Get the embedding vector for a specific playlist.

        Args:
            playlist_id (int): ID of the playlist

        Returns:
            np.ndarray: Embedding vector for the playlist, None if not found
        """
        if playlist_id in self.playlist_encoder:
            index = self.playlist_encoder[playlist_id]
            return self.model.get_layer('playlist_embedding').get_weights()[0][index]
        return None
    
    def recommend_for_playlist(self, playlist_id: int, n_recommendations: int=10) -> List[Tuple[int, float]]:
        """
        Generate song recommendations for playlist with playlist_id

        Args:
            playlist_id (int): ID of the playlist
            n_recommendations (int, optional): Number of recommendations to return. Defaults to 10

        Returns:
            List[Tuple[int, float]]:
                List of tuples containing song IDs and their scores
        """
        
        if not self.model:
            if not self.load_model():
                print("NEMA MODELA")
                return []
        
        if playlist_id not in self.playlist_encoder:
            print(f"Playlist {playlist_id} not in training data")
            return []
        
        playlist_idx = self.playlist_encoder[playlist_id]
        playlist = Playlist.objects.get(id=playlist_id)
        existing_songs_ids = set(playlist.songs.values_list('id', flat=True))
        
        # Get predscitons for all songs
        all_songs_indices = np.array(list(range(len(self.song_encoder))))
        playlist_indices = np.full_like(all_songs_indices, playlist_idx)
        
        predictions = self.model.predict([playlist_indices, all_songs_indices], batch_size=1024)
        predictions = predictions.flatten()
        
        # Sort by score and filter out existing songs
        song_scores = []
        for song_idx, score in enumerate(predictions):
            if song_idx in self.song_decoder:
                song_id = self.song_decoder[song_idx]
                if song_id not in existing_songs_ids:
                    song_scores.append((song_id, float(score)))
                    
        song_scores.sort(key=lambda x: x[1], reverse=True)
        return song_scores[:n_recommendations]
    
    
    def update_playlist_recommendations(self, playlist_id: int, n_recommendations: int=10):
        """
        Update recommendations for a specific playlist

        Args:
            playlist_id (int): ID of the playlist
            n_recommendations (int, optional): Number of recommendations to generate
        """
        recommendations = self.recommend_for_playlist(playlist_id, n_recommendations)
        
        if not recommendations:
            return
        
        PlaylistRecommendation.objects.filter(playlist_id=playlist_id).delete()
        
        for song_id, score in recommendations:
            try:  
                PlaylistRecommendation.objects.create(
                    playlist_id=playlist_id,
                    song_id=song_id,
                    score=score,
                    created_at=timezone.now()
                )
            except Song.DoesNotExist:
                print(f"Song with ID {song_id} does not exist")
                continue
    
    
    def update_all_recommendations(self, n_recommendations: int=10):
        """
        Update recommendations for all playlists in the database.

        Args:
            n_recommendations (int, optional): Number of recommendations to generate for each playlist
        """
        playlists = Playlist.objects.all()
        
        for playlist in playlists:
            self.update_playlist_recommendations(playlist.id, n_recommendations)
            print(f"Updated recommendations for playlist {playlist.id}")