import numpy as np
import pandas as pd
import tensorflow as tf
from typing import List, Dict, Tuple, Optional
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
from django.db.models import Q, F, Count, Avg
from music.models import Song, Playlist
from spotify.utils import get_track_audio_features, get_multiple_track_audio_features
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
        self.model_dir = os.path.join(settings.MEDIA_ROOT, 'models')
        self.model_path = os.path.join(self.model_dir, 'content_model.h5')
        os.makedirs(self.model_dir, exist_ok=True)
        self.autoencoder = None
    
    
    def get_song_features(self, song: Song) -> Optional[Dict[str, float]]:
        """
        Get audio features for a given song with improved error handling.

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
        
        if len(features) == len(feature_names):
            return self._enhance_features(features)
        
        if song.spotify_id:
            try:
                logger.info(f"Fetching audio features for song: {song.name} (ID: {song.spotify_id})")
                audio_features = get_track_audio_features(song.spotify_id)
                
                if audio_features:
                    updated = False
                    for feature in feature_names:
                        if feature not in features and feature in audio_features:
                            features[feature] = audio_features[feature]
                            setattr(song, feature, audio_features[feature])
                            updated = True
                    
                    if updated:
                        try:
                            song.save()
                            logger.info(f"Updated audio features for song: {song.name}")
                        except Exception as e:
                            logger.error(f"Error saving audio features for song {song.id}: {e}")
                else:
                    logger.warning(f"No audio features returned for song: {song.name} (ID: {song.spotify_id})")
                    
            except Exception as e:
                logger.error(f"Error fetching audio features for song {song.id}: {e}")
        
        # Use default values for missing features
        for feature in feature_names:
            if feature not in features:
                default_value = 0.5 if feature != 'instrumentalness' else 0.0
                features[feature] = default_value
                logger.debug(f"Using default value {default_value} for {feature} on song {song.id}")
        
        return self._enhance_features(features) if features else {}
    
    def _enhance_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """Add derived features to the feature dictionary"""
        enhanced = features.copy()
        
        if 'energy' in enhanced and 'valence' in enhanced:
            enhanced['mood'] = (enhanced['energy'] + enhanced['valence']) / 2
        
        if 'danceability' in enhanced and 'energy' in enhanced:
            enhanced['party_factor'] = (enhanced['danceability'] * 0.6 + enhanced['energy'] * 0.4)
        
        # Normalize tempo
        if 'tempo' in enhanced:
            enhanced['tempo_normalized'] = (enhanced['tempo'] - 60) / 140
            enhanced['tempo_normalized'] = max(0, min(1, enhanced['tempo_normalized']))  # Clamp to 0-1
        
        return enhanced
    
    def batch_get_song_features(self, songs: List[Song]) -> Dict[int, Dict[str, float]]:
        """
        Efficiently get features for multiple songs using batch API calls.
        
        Args:
            songs (List[Song]): List of songs to get features for.
            
        Returns:
            Dict[int, Dict[str, float]]: Dictionary mapping song IDs to their features.
        """
        features_map = {}
        songs_needing_api = []
        
        feature_names = [
            'tempo', 'energy', 'danceability', 'valence',
            'acousticness', 'instrumentalness'
        ]
        
        for song in songs:
            features = {}
            for feature in feature_names:
                value = getattr(song, feature, None)
                if value is not None:
                    features[feature] = value
            
            if len(features) == len(feature_names):
                features_map[song.id] = self._enhance_features(features)
            else:
                songs_needing_api.append(song)
        
        if songs_needing_api:
            spotify_ids = [song.spotify_id for song in songs_needing_api if song.spotify_id]
            
            if spotify_ids:
                try:
                    logger.info(f"Batch fetching audio features for {len(spotify_ids)} songs")
                    batch_features = get_multiple_track_audio_features(spotify_ids)
                    
                    for song in songs_needing_api:
                        if song.spotify_id and song.spotify_id in batch_features:
                            audio_features = batch_features[song.spotify_id]
                            
                            features = {}
                            updated = False
                            
                            for feature in feature_names:
                                db_value = getattr(song, feature, None)
                                if db_value is not None:
                                    features[feature] = db_value
                                elif feature in audio_features:
                                    features[feature] = audio_features[feature]
                                    setattr(song, feature, audio_features[feature])
                                    updated = True
                                else:
                                    default_value = 0.5 if feature != 'instrumentalness' else 0.0
                                    features[feature] = default_value
                            
                            if updated:
                                try:
                                    song.save()
                                except Exception as e:
                                    logger.error(f"Error saving batch features for song {song.id}: {e}")
                            
                            features_map[song.id] = self._enhance_features(features)
                        else:
                            features = {}
                            for feature in feature_names:
                                db_value = getattr(song, feature, None)
                                if db_value is not None:
                                    features[feature] = db_value
                                else:
                                    default_value = 0.5 if feature != 'instrumentalness' else 0.0
                                    features[feature] = default_value
                            
                            features_map[song.id] = self._enhance_features(features)
                
                except Exception as e:
                    logger.error(f"Error in batch feature fetching: {e}")
                    for song in songs_needing_api:
                        if song.id not in features_map:
                            features = {}
                            for feature in feature_names:
                                db_value = getattr(song, feature, None)
                                if db_value is not None:
                                    features[feature] = db_value
                                else:
                                    default_value = 0.5 if feature != 'instrumentalness' else 0.0
                                    features[feature] = default_value
                            
                            features_map[song.id] = self._enhance_features(features)
        
        return features_map

    def create_feature_vector(self, songs: List[Song]) -> Tuple[np.ndarray, List[Song]]:
        """
        Create feature matrix for songs using batch processing
        
        Args:
            songs (List[Song]): List of Song objects.
        
        Returns:
            Tuple[np.ndarray, List[Song]]: A tuple containing the feature matrix and a list of valid songs.
        """
        if not songs:
            return np.array([]), []
        
        features_map = self.batch_get_song_features(songs)
        
        feature_list = []
        valid_songs = []
        
        for song in songs:
            if song.id in features_map:
                features = features_map[song.id]
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
        
        all_songs = Song.objects.filter(spotify_id__isnull=False)[:5000]  # Limit for training
        
        features, valid_songs = self.create_feature_vector(all_songs)
        if len(features) == 0:
            logger.warning("No valid songs found for training autoencoder.")
            return None
        
        logger.info(f"Training autoencoder with {len(features)} songs")
        
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
        autoencoder_path = os.path.join(self.model_dir, 'autoencoder.keras')
        self.autoencoder.save(autoencoder_path)
        
        encoder_path = os.path.join(self.model_dir, 'encoder.keras')
        self.encoder.save(encoder_path)

        scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
    
    def load_models(self) -> bool:
        """Load pre-trained models from disk.

        Returns:
            bool: True if models are loaded successfully, False otherwise.
        """
        try:
            autoencoder_path = os.path.join(self.model_dir, 'autoencoder.keras')
            self.autoencoder = tf.keras.models.load_model(autoencoder_path)
            
            encoder_path = os.path.join(self.model_dir, 'encoder.keras')
            self.encoder = tf.keras.models.load_model(encoder_path)
            
            scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
            with open(scaler_path, 'rb') as f:
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
        songs = list(playlist.songs.all())
        if not songs:
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
    
    def recommend_by_audio_features(self, playlist: Playlist, n_recommendations: int = 10) -> List[Tuple[Song, float]]:
        """
        Recommend songs based on audio features similarity.

        Args:
            playlist (Playlist): The playlist to base recommendations on.
            n_recommendations (int): Number of songs to recommend.

        Returns:
            List[Tuple[Song, float]]: List of recommended songs with similarity scores.
        """
        playlist_profile = self.calculate_playlist_profile(playlist)
        if not playlist_profile:
            logger.warning("No valid features found for playlist.")
            return []
        
        existing_ids = set(playlist.songs.values_list('id', flat=True))
        

        candidate_songs = list(Song.objects.exclude(id__in=existing_ids)
                              .filter(spotify_id__isnull=False)[:1000])  # Limit for performance
        
        if not candidate_songs:
            logger.warning("No candidate songs found for recommendations.")
            return []
        
        # Batch get features for all candidates
        features_map = self.batch_get_song_features(candidate_songs)
        
        similarities = []
        
        playlist_vector = np.array([
            playlist_profile.get('tempo_normalized', 0.5),
            playlist_profile.get('energy', 0.5),
            playlist_profile.get('danceability', 0.5),
            playlist_profile.get('valence', 0.5),
            playlist_profile.get('acousticness', 0.5),
            playlist_profile.get('instrumentalness', 0.0)
        ])
        
        playlist_artists = set(playlist.songs.values_list('artist', flat=True))
        
        for song in candidate_songs:
            if song.id not in features_map:
                continue
                
            features = features_map[song.id]
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
            if song.artist in playlist_artists:
                similarity *= 1.1
            
            similarities.append((song, float(similarity)))

        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:n_recommendations]
    
    def recommend_by_mood(self, playlist: Playlist, n_recommendations: int = 10) -> List[Tuple[Song, float]]:
        """
        Recommend songs based on mood profile of the playlist.

        Args:
            playlist (Playlist): The playlist to base recommendations on.
            n_recommendations (int): Number of songs to recommend.

        Returns:
            List[Tuple[Song, float]]: List of recommended songs with their similarity scores.
        """
        
        profile = self.calculate_playlist_profile(playlist)
        if not profile:
            logger.warning("No valid features found for playlist.")
            return []
        
        energy = profile.get('energy', 0.5)
        valence = profile.get('valence', 0.5)
        
        if energy > 0.6 and valence > 0.6:
            mood = 'happy'
            mood_query = Q(energy__gte=0.5, valence__gte=0.5)
        elif energy > 0.6 and valence <= 0.4:
            mood = 'angry'
            mood_query = Q(energy__gte=0.5, valence__lte=0.5)
        elif energy <= 0.4 and valence <= 0.4:
            mood = 'sad'
            mood_query = Q(energy__lte=0.5, valence__lte=0.5)
        else:
            mood = 'relaxed'
            mood_query = Q(energy__lte=0.5, valence__gte=0.5)
            
        existing_ids = set(playlist.songs.values_list('id', flat=True))
        matching_songs = list(Song.objects.filter(mood_query)
                             .exclude(id__in=existing_ids)
                             .filter(spotify_id__isnull=False)
                             .order_by('-popularity')[:n_recommendations * 2])
        
        recommendations = []
        features_map = self.batch_get_song_features(matching_songs)
        
        for song in matching_songs:
            if song.id not in features_map:
                continue
                
            features = features_map[song.id]
            mood_distance = (
                abs(features.get('energy', 0.5) - energy) +
                abs(features.get('valence', 0.5) - valence)
            )
            score = 1.0 - (mood_distance / 2.0)
            recommendations.append((song, float(score)))

        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:n_recommendations]