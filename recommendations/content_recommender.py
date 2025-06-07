import numpy as np
import pandas as pd
import tensorflow as tf
from typing import List, Dict, Tuple, Optional
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
from django.db.models import Q, F, Count, Avg
from music.models import Song, Playlist
from spotify.utils import get_track_audio_features
from tensorflow.keras import layers, models
import pickle
import os
from django.conf import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ContentBasedRecommender:
    def __init__(self):
        self.scaler = StandardScaler()
        self.feature_weights = {
            'tempo': 0.20,
            'energy': 0.25,
            'danceability': 0.20,
            'valence': 0.15,
            'acousticness': 0.10,
            'instrumentalness': 0.10,
        }
        self.model_path = os.path.join(settings.MEDIA_ROOT, 'content_model.h5')
        os.makedirs(self.model_path, exist_ok=True)
        self.autoencoder = None
    
    
    def get_song_features(self, song: Song) -> Optional[Dict[str, float]]:
        """
        Get audio features for a given song.

        Args:
            song (Song): The song object to get features from.

        Returns:
            Optional[Dict[str, float]]: A dictionary of audio features if available,
            otherwise None.
        """
        features = {}
        
        feature_names = [
            'tempo', 'energy', 'danceability', 'valence',
            'acousticness', 'instrumentalness'
        ]
        
        for feature in feature_names:
            value = getattr(song, feature, None)
            if value is not None:
                features[feature] = value
                
        if len(features) < len(feature_names):
            try:
                audio_features = get_track_audio_features(song.spotify_id)
                if audio_features:
                    for feature in feature_names:
                        if feature not in features and feature in audio_features:
                            features[feature] = audio_features[feature]
                            setattr(song, feature, audio_features[feature])
                            song.save()
            except Exception as e:
                logger.error(f"Error fetching audio features for song {song.id}: {e}")
                
        if 'energy' in features and 'valence' in features:
            features['mood'] = (features['energy'] + features['valence']) / 2
        
        if 'danceability' in features and 'energy' in features:
            features['party_factor'] = (features['danceability'] * 0.6 + features['energy'] * 0.4)
            
        
        if 'tempo' in features:
            features['tempo_normalized'] = (features['tempo'] - 60) / 140

        return features if features else None
    

    def create_feature_vector(self, songs: List[Song]) -> Tuple[np.ndarray, List[str]]:
        """
        Create feature matrix for songs
        
        Args:
            songs (List[Song]): List of Song objects.
        
        Returns:
            Tuple[np.ndarray, List[str]]: A tuple containing the feature matrix and a list of valid song IDs.
        """
        feature_list = []
        valid_songs = []
        
        for song in songs:
            features = self.get_song_features(song)
            if features:
                feature_vector = np.array([
                    features.get('tempo_normalized', 0.5),
                    features.get('energy', 0.5),
                    features.get('danceability', 0.5),
                    features.get('valence', 0.5),
                    features.get('acousticness', 0.5),
                    features.get('instrumentalness', 0.0)
                ])
                feature_list.append(feature_vector)
                valid_songs.append(song)
                
        if not feature_list:
            return np.array([]), []
        return np.array(feature_list), valid_songs

    def build_autoencoder(self, input_dim: int, encoding_dim: int = 32) -> Tuple[tf.keras.Model, tf.keras.Model]:
        """
        Build an autoencoder model to learn compressed representation
        of song features

        Args:
            input_dim (int): The dimensionality of the input features.
            encoding_dim (int, optional): The dimensionality of the encoding layer. Defaults to 32.
        
        Returns:
            Tuple[tf.keras.Model, tf.keras.Model]: Autoencoder model and encoder model.
        """
        # Encoder
        input_layer = layers.Input(shape=(input_dim,))
        encoded = layers.Dense(64, activation='relu')(input_layer)
        encoded = layers.BatchNormalization()(encoded)
        encoded = layers.Dropout(0.2)(encoded)
        encoded = layers.Dense(encoding_dim, activation='relu', name='encoding')(encoded)

        # Decoder
        decoded = layers.Dense(64, activation='relu')(encoded)
        decoded = layers.BatchNormalization()(decoded)
        decoded = layers.Dropout(0.2)(decoded)
        decoded = layers.Dense(input_dim, activation='sigmoid')(decoded)
        
        # Models
        autoencoder = models.Model(inputs=input_layer, outputs=decoded)
        encoder = models.Model(inputs=input_layer, outputs=encoded)
        
        autoencoder.compile(optimizer='adam', loss='mse', metrics=['mae'])
        
        return autoencoder, encoder
    
    def train_autoencoder(self, n_epochs: int = 50):
        logger.info("Training autoencoder")
        
        all_songs = Song.objects.all()
        
        features, valid_songs = self.create_feature_vector(all_songs)
        if len(features) == 0:
            logger.warning("No valid songs found for training autoencoder.")
            return None
        
        features_scaled = self.scaler.fit_transform(features)

        self.autoencoder, self.encoder = self.build_autoencoder(input_dim=features_scaled.shape[1])
        history = self.autoencoder.fit(
            features_scaled, features_scaled,
            epochs=n_epochs,
            batch_size=32,
            validation_split=0.1,
            verbose=1
        )
        self.save_models()
        
        return history
    
    
    def save_models(self):
        self.autoencoder.save(self.model_path, 'autoencoder.h5')
        self.encoder.save(self.model_path, 'encoder.h5')
        
        with open(os.path.join(self.model_path, 'scaler.pkl'), 'wb') as f:
            pickle.dump(self.scaler, f)
    
    
    def load_models(self) -> bool:
        """Load pre-trained models from disk.

        Returns:
            bool: True if models are loaded successfully, False otherwise.
        """
        try:
            self.autoencoder = tf.keras.models.load_model(
                os.path.join(self.model_path, 'autoencoder.h5')
            )
            self.encoder = tf.keras.models.load_model(
                os.path.join(self.model_path, 'encoder.h5')
            )
            with open(os.path.join(self.model_path, 'scaler.pkl'), 'rb') as f:
                self.scaler = pickle.load(f)
            return True
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False
     
     
    def calculate_playlist_profile(self, playlist: Playlist) -> Dict[str, float]:
        """
        Calculate the average and diversity of audio features for a given playlist.

        Args:
            playlist (Playlist): The playlist to profile.

        Returns:
            Dict[str, float]: Averages of features and their diversity
        """
        songs = playlist.songs.all()
        if not songs.exists():
            return {}
        
        features, valid_songs = self.create_feature_vector(songs)
        if len(features) == 0:
            return {}
        
        # Calculate weighted averages
        avg_features = np.mean(features, axis=0)
        
        feature_names = [
            'tempo_normalized', 'energy', 'danceability', 
            'valence', 'acousticness', 'instrumentalness'
        ]
        
        profile = {name: float(value) for name, value in zip(feature_names, avg_features)}
        
        # Calculate diversity
        if len(features) > 1:
            diversity = np.std(features, axis=0)
            for i, name in enumerate(feature_names):
                profile[f'{name}_diversity'] = float(diversity[i])
                
        return profile
    
    
    def recommend_by_audio_features(self, playlist: Playlist, n_recommendations: int = 10) -> List[Song]:
        """
        Recommend songs based on audio features similarity.

        Args:
            playlist (Playlist): The playlist to base recommendations on.
            n_recommendations (int): Number of songs to recommend.

        Returns:
            List[Song]: List of recommended songs.
        """
        playlist_profile = self.calculate_playlist_profile(playlist)
        if not playlist_profile:
            logger.warning("No valid features found for playlist.")
            return []
        
        existing_ids = set(playlist.songs.values_list('spotify_id', flat=True))
        
        # Get candidates
        candidate_songs = Song.objects.exclude(id__in=existing_ids)[:1000] # Limit to 1000 for performance
        
        similarities = []
        
        playlist_vector = np.array([
            playlist_profile.get('tempo_normalized', 0.5),
            playlist_profile.get('energy', 0.5),
            playlist_profile.get('danceability', 0.5),
            playlist_profile.get('valence', 0.5),
            playlist_profile.get('acousticness', 0.5),
            playlist_profile.get('instrumentalness', 0.0)
        ])
        
        for song in candidate_songs:
            features = self.get_song_features(song)
            if features:
                song_vector = np.array([
                    features.get('tempo_normalized', 0.5),
                    features.get('energy', 0.5),
                    features.get('danceability', 0.5),
                    features.get('valence', 0.5),
                    features.get('acousticness', 0.5),
                    features.get('instrumentalness', 0.0)
                ])

                # Weighted cosine similarity
                weights = np.array(list(self.feature_weights.values()))
                weighted_playlist = playlist_vector * weights
                weighted_song = song_vector * weights
                
                similarity = cosine_similarity(weighted_playlist.reshape(1, -1), weighted_song.reshape(1, -1))[0][0]
                
                # Artist boost
                playlist_artists = set(playlist.songs.values_list('artist', flat=True))
                if song.artist in playlist_artists:
                    similarity *= 1.1
                
                similarities.append((song, float(similarity)))
                
                

        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:n_recommendations]