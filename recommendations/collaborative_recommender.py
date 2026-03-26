import logging
import os
import pickle
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import tensorflow as tf
from django.conf import settings
from django.utils import timezone

from music.models import Playlist, Song
from recommendations.models import PlaylistRecommendation

logger = logging.getLogger(__name__)


class PlaylistRecommender:
    """Collaborative filtering recommender using matrix factorization with TensorFlow.

    Trains a neural matrix factorization model on implicit playlist-song interactions.
    Uses binary cross-entropy with negative sampling — the correct objective for implicit
    feedback data (as opposed to MSE on all-ones ratings).

    Model architecture:
        - Embedding lookup for playlists and songs (n_factors dimensions each)
        - Per-entity bias terms
        - Dot product of embeddings + bias → sigmoid → interaction probability

    Versioned model saves: each call to save_model() creates a timestamped directory
    and writes a 'latest.txt' pointer so load_model() always loads the most recent version.
    """

    def __init__(
        self,
        n_factors: int = 50,
        learning_rate: float = 0.001,
        n_epochs: int = 50,
        batch_size: int = 128,
    ) -> None:
        """Initialize hyperparameters and paths.

        Args:
            n_factors: Number of latent embedding dimensions. Defaults to 50.
            learning_rate: Adam optimizer learning rate. Defaults to 0.001.
            n_epochs: Maximum training epochs (EarlyStopping may stop earlier). Defaults to 50.
            batch_size: Mini-batch size. Defaults to 128.
        """
        self.n_factors = n_factors
        self.learning_rate = learning_rate
        self.n_epochs = n_epochs
        self.batch_size = batch_size
        self.model: Optional[tf.keras.Model] = None
        self.playlist_encoder: Dict[int, int] = {}  # {playlist_id: index}
        self.song_encoder: Dict[int, int] = {}       # {song_id: index}
        self.playlist_decoder: Dict[int, int] = {}   # {index: playlist_id}
        self.song_decoder: Dict[int, int] = {}       # {index: song_id}
        self.model_path = os.path.join(settings.MEDIA_ROOT, 'recommendation_model')
        os.makedirs(self.model_path, exist_ok=True)

    # ── Data preparation ──────────────────────────────────────────────────────

    def prepare_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Load positive playlist-song interactions and build ID encoders.

        Returns:
            Tuple of (playlist_indices, song_indices, ratings) where ratings are
            all 1.0 (positive interactions only). Call _sample_negatives_indexed()
            afterwards to add negative samples for training.
        """
        playlists = Playlist.objects.prefetch_related('songs').filter(songs__isnull=False).distinct()

        interactions = []
        for playlist in playlists:
            for song in playlist.songs.all():
                interactions.append({
                    'playlist_id': playlist.id,
                    'song_id': song.id,
                    'rating': 1.0,
                })

        if not interactions:
            return np.array([]), np.array([]), np.array([])

        df = pd.DataFrame(interactions)

        unique_playlists = df['playlist_id'].unique()
        unique_songs = df['song_id'].unique()

        self.playlist_encoder = {pid: idx for idx, pid in enumerate(unique_playlists)}
        self.song_encoder = {sid: idx for idx, sid in enumerate(unique_songs)}
        self.playlist_decoder = {idx: pid for pid, idx in self.playlist_encoder.items()}
        self.song_decoder = {idx: int(sid) for sid, idx in self.song_encoder.items()}

        playlist_indices = df['playlist_id'].map(self.playlist_encoder).values
        song_indices = df['song_id'].map(self.song_encoder).values
        ratings = df['rating'].values

        logger.info(
            "Loaded %d positive interactions (%d playlists, %d songs)",
            len(interactions),
            len(unique_playlists),
            len(unique_songs),
        )
        return playlist_indices, song_indices, ratings

    def _sample_negatives_indexed(
        self,
        playlist_indices: np.ndarray,
        song_indices: np.ndarray,
        n_neg_per_pos: int = 4,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Augment positive interactions with sampled negatives for BCE training.

        For each playlist, samples songs NOT present in that playlist as negatives
        (label 0). This is the standard approach for implicit feedback collaborative
        filtering (Rendle et al. 2009 — BPR; He et al. 2017 — NCF).

        Args:
            playlist_indices: Encoded playlist indices for positive pairs.
            song_indices: Encoded song indices for positive pairs.
            n_neg_per_pos: Negative samples per positive interaction. Defaults to 4.

        Returns:
            Tuple of (all_playlist_indices, all_song_indices, all_labels) with
            positives (label=1) and negatives (label=0) shuffled together.
        """
        n_songs = len(self.song_encoder)
        rng = np.random.default_rng(42)
        neg_playlists: List[int] = []
        neg_songs: List[int] = []

        for p_idx in np.unique(playlist_indices):
            pos_songs = set(song_indices[playlist_indices == p_idx].tolist())
            neg_candidates = np.array([i for i in range(n_songs) if i not in pos_songs])
            if len(neg_candidates) == 0:
                continue
            n_neg = min(len(pos_songs) * n_neg_per_pos, len(neg_candidates))
            sampled = rng.choice(neg_candidates, n_neg, replace=False)
            neg_playlists.extend([int(p_idx)] * n_neg)
            neg_songs.extend(sampled.tolist())

        if not neg_playlists:
            return playlist_indices, song_indices, np.ones(len(playlist_indices))

        neg_p = np.array(neg_playlists)
        neg_s = np.array(neg_songs)
        all_p = np.concatenate([playlist_indices, neg_p])
        all_s = np.concatenate([song_indices, neg_s])
        all_r = np.concatenate([np.ones(len(playlist_indices)), np.zeros(len(neg_p))])

        shuffle_idx = rng.permutation(len(all_p))
        return all_p[shuffle_idx], all_s[shuffle_idx], all_r[shuffle_idx]

    # ── Model architecture ────────────────────────────────────────────────────

    def build_model(self, n_playlists: int, n_songs: int) -> tf.keras.Model:
        """Build the neural matrix factorization model.

        Architecture: embedding lookup → dot product + bias terms → sigmoid.
        Uses binary cross-entropy loss, appropriate for implicit feedback with
        negative sampling.

        Args:
            n_playlists: Number of unique playlists (vocabulary size for playlist embedding).
            n_songs: Number of unique songs (vocabulary size for song embedding).

        Returns:
            Compiled Keras model ready for training.
        """
        playlist_input = tf.keras.layers.Input(shape=(1,), name='playlist_input')
        song_input = tf.keras.layers.Input(shape=(1,), name='song_input')

        playlist_embedding = tf.keras.layers.Embedding(
            input_dim=n_playlists,
            output_dim=self.n_factors,
            name='playlist_embedding',
            embeddings_regularizer=tf.keras.regularizers.l2(1e-5),
        )(playlist_input)
        song_embedding = tf.keras.layers.Embedding(
            input_dim=n_songs,
            output_dim=self.n_factors,
            name='song_embedding',
            embeddings_regularizer=tf.keras.regularizers.l2(1e-5),
        )(song_input)

        playlist_vec = tf.keras.layers.Flatten(name='playlist_flatten')(playlist_embedding)
        song_vec = tf.keras.layers.Flatten(name='song_flatten')(song_embedding)

        dot_product = tf.keras.layers.Dot(axes=1, name='dot_product')([playlist_vec, song_vec])

        playlist_bias = tf.keras.layers.Embedding(
            input_dim=n_playlists, output_dim=1, name='playlist_bias'
        )(playlist_input)
        song_bias = tf.keras.layers.Embedding(
            input_dim=n_songs, output_dim=1, name='song_bias'
        )(song_input)
        playlist_bias = tf.keras.layers.Flatten()(playlist_bias)
        song_bias = tf.keras.layers.Flatten()(song_bias)

        logits = tf.keras.layers.Add(name='logits')([dot_product, playlist_bias, song_bias])
        output = tf.keras.layers.Activation('sigmoid', name='output')(logits)

        model = tf.keras.Model(
            inputs=[playlist_input, song_input],
            outputs=output,
            name='PlaylistRecommender',
        )
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss='binary_crossentropy',
            metrics=['accuracy', tf.keras.metrics.AUC(name='auc')],
        )
        return model

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, negative_sample_ratio: int = 4) -> Optional[tf.keras.callbacks.History]:
        """Train the model on all available data with negative sampling.

        Uses EarlyStopping (patience=5) on val_loss and ReduceLROnPlateau to avoid
        manual epoch tuning. Model is saved with a versioned timestamp after training.

        Args:
            negative_sample_ratio: Negatives sampled per positive interaction. Defaults to 4.

        Returns:
            Keras History object if training succeeded, None if data is unavailable.
        """
        logger.info("Preparing training data")
        playlist_indices, song_indices, _ = self.prepare_data()

        if len(playlist_indices) == 0:
            logger.warning("No interaction data available for training")
            return None

        playlist_indices, song_indices, ratings = self._sample_negatives_indexed(
            playlist_indices, song_indices, n_neg_per_pos=negative_sample_ratio
        )

        n_playlists = len(self.playlist_encoder)
        n_songs = len(self.song_encoder)
        logger.info(
            "Training on %d samples (%d playlists, %d songs)",
            len(ratings),
            n_playlists,
            n_songs,
        )

        self.model = self.build_model(n_playlists, n_songs)

        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=5,
                restore_best_weights=True,
                verbose=1,
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=3,
                min_lr=1e-6,
            ),
        ]

        history = self.model.fit(
            [playlist_indices, song_indices],
            ratings,
            batch_size=self.batch_size,
            epochs=self.n_epochs,
            validation_split=0.1,
            callbacks=callbacks,
            verbose=0,
        )

        epochs_run = len(history.history['loss'])
        final_val_loss = history.history['val_loss'][-1]
        final_val_auc = history.history.get('val_auc', [None])[-1]
        logger.info(
            "Training complete: %d epochs, val_loss=%.4f, val_auc=%s",
            epochs_run,
            final_val_loss,
            f"{final_val_auc:.4f}" if final_val_auc is not None else "N/A",
        )

        self.save_model()
        return history

    def train_with_evaluation(
        self,
        test_fraction: float = 0.2,
        k: int = 10,
        negative_sample_ratio: int = 4,
    ) -> Optional[Dict[str, Any]]:
        """Train with a held-out split and return offline ranking metrics.

        Splits positive interactions into train/test BEFORE adding negatives, so the
        test set contains only genuine positives not seen during training.

        Metrics computed:
            - Precision@K: fraction of top-K recommendations that are held-out positives
            - Recall@K: fraction of held-out positives recovered in top-K
            - NDCG@K: normalised discounted cumulative gain (position-sensitive)

        Args:
            test_fraction: Fraction of positive interactions to hold out. Defaults to 0.2.
            k: Ranking cutoff for all metrics. Defaults to 10.
            negative_sample_ratio: Negatives per positive in training. Defaults to 4.

        Returns:
            Dict with keys 'history' (Keras History) and 'metrics' (evaluation dict),
            or None if there is insufficient data.
        """
        logger.info("Preparing data for held-out evaluation (test_fraction=%.2f)", test_fraction)
        playlist_indices, song_indices, _ = self.prepare_data()

        if len(playlist_indices) == 0:
            logger.warning("No training data available")
            return None

        n_total = len(playlist_indices)
        n_test = max(1, int(n_total * test_fraction))

        rng = np.random.default_rng(42)
        test_idx = rng.choice(n_total, n_test, replace=False)
        train_idx = np.setdiff1d(np.arange(n_total), test_idx)

        train_p = playlist_indices[train_idx]
        train_s = song_indices[train_idx]
        test_p = playlist_indices[test_idx]
        test_s = song_indices[test_idx]

        # Add negatives only to the training split
        train_p, train_s, train_r = self._sample_negatives_indexed(
            train_p, train_s, n_neg_per_pos=negative_sample_ratio
        )

        n_playlists = len(self.playlist_encoder)
        n_songs = len(self.song_encoder)
        self.model = self.build_model(n_playlists, n_songs)

        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss', patience=5, restore_best_weights=True
            ),
        ]

        history = self.model.fit(
            [train_p, train_s],
            train_r,
            batch_size=self.batch_size,
            epochs=self.n_epochs,
            validation_split=0.1,
            callbacks=callbacks,
            verbose=0,
        )

        logger.info("Training complete, evaluating on %d held-out interactions", n_test)
        metrics = self._evaluate_on_holdout(test_p, test_s, k=k)

        self.save_model()
        return {'history': history, 'metrics': metrics}

    def _evaluate_on_holdout(
        self,
        test_playlist_indices: np.ndarray,
        test_song_indices: np.ndarray,
        k: int = 10,
    ) -> Dict[str, float]:
        """Compute Precision@K, Recall@K, and NDCG@K on held-out interactions.

        Args:
            test_playlist_indices: Encoded playlist indices from the test split.
            test_song_indices: Encoded song indices from the test split.
            k: Ranking cutoff. Defaults to 10.

        Returns:
            Dict with precision@k, recall@k, ndcg@k, and n_test_playlists.
        """
        from collections import defaultdict

        test_items: Dict[int, set] = defaultdict(set)
        for p_idx, s_idx in zip(test_playlist_indices.tolist(), test_song_indices.tolist()):
            test_items[int(p_idx)].add(int(s_idx))

        n_songs = len(self.song_encoder)
        all_song_indices = np.arange(n_songs)

        precisions, recalls, ndcgs = [], [], []

        for p_idx, relevant_items in test_items.items():
            p_indices = np.full(n_songs, p_idx)
            preds = self.model.predict(
                [p_indices, all_song_indices], batch_size=1024, verbose=0
            )
            preds = preds.flatten()

            top_k = np.argsort(preds)[::-1][:k]
            hits = len(set(top_k.tolist()) & relevant_items)

            precisions.append(hits / k)
            recalls.append(hits / len(relevant_items))

            dcg = sum(
                1.0 / np.log2(rank + 2)
                for rank, item in enumerate(top_k.tolist())
                if item in relevant_items
            )
            ideal_hits = min(k, len(relevant_items))
            idcg = sum(1.0 / np.log2(rank + 2) for rank in range(ideal_hits))
            ndcgs.append(dcg / idcg if idcg > 0 else 0.0)

        metrics = {
            f'precision@{k}': float(np.mean(precisions)) if precisions else 0.0,
            f'recall@{k}': float(np.mean(recalls)) if recalls else 0.0,
            f'ndcg@{k}': float(np.mean(ndcgs)) if ndcgs else 0.0,
            'n_test_playlists': len(test_items),
        }
        logger.info("Evaluation metrics: %s", metrics)
        return metrics

    # ── Persistence ───────────────────────────────────────────────────────────

    def save_model(self) -> None:
        """Persist the trained model and encoders with a versioned timestamp.

        Creates a subdirectory named by timestamp (YYYYMMDD_HHMMSS) and writes
        a 'latest.txt' pointer so load_model() always loads the most recent version.
        Legacy models saved directly in model_path are still loadable.
        """
        version = datetime.now().strftime('%Y%m%d_%H%M%S')
        versioned_path = os.path.join(self.model_path, version)
        os.makedirs(versioned_path, exist_ok=True)

        self.model.save(os.path.join(versioned_path, 'model.keras'))
        with open(os.path.join(versioned_path, 'encoders.pkl'), 'wb') as f:
            pickle.dump(
                {
                    'playlist_encoder': self.playlist_encoder,
                    'song_encoder': self.song_encoder,
                    'playlist_decoder': self.playlist_decoder,
                    'song_decoder': self.song_decoder,
                },
                f,
            )

        latest_pointer = os.path.join(self.model_path, 'latest.txt')
        with open(latest_pointer, 'w') as f:
            f.write(version)

        logger.info("Model saved as version %s", version)

    def load_model(self) -> bool:
        """Load the most recent model version from disk.

        Reads 'latest.txt' to find the versioned directory. Falls back to the
        model_path root for backwards compatibility with pre-versioning saves.

        Returns:
            True if the model and encoders were loaded successfully, False otherwise.
        """
        try:
            latest_pointer = os.path.join(self.model_path, 'latest.txt')
            if os.path.exists(latest_pointer):
                with open(latest_pointer) as f:
                    version = f.read().strip()
                load_path = os.path.join(self.model_path, version)
            else:
                load_path = self.model_path  # legacy path

            self.model = tf.keras.models.load_model(os.path.join(load_path, 'model.keras'))
            with open(os.path.join(load_path, 'encoders.pkl'), 'rb') as f:
                encoders = pickle.load(f)
                self.playlist_encoder = encoders['playlist_encoder']
                self.song_encoder = encoders['song_encoder']
                self.playlist_decoder = encoders['playlist_decoder']
                self.song_decoder = encoders['song_decoder']
            return True
        except Exception as e:
            logger.error("Error loading model: %s", e)
            return False

    # ── Inference ─────────────────────────────────────────────────────────────

    def get_playlist_embedding(self, playlist_id: int) -> Optional[np.ndarray]:
        """Return the learned embedding vector for a playlist.

        Args:
            playlist_id: Database ID of the playlist.

        Returns:
            Embedding vector of shape (n_factors,), or None if playlist was not in
            the training data.
        """
        if playlist_id in self.playlist_encoder:
            index = self.playlist_encoder[playlist_id]
            return self.model.get_layer('playlist_embedding').get_weights()[0][index]
        return None

    def recommend_for_playlist(
        self, playlist_id: int, n_recommendations: int = 10
    ) -> List[Tuple[int, float]]:
        """Generate song recommendations for a playlist using the trained model.

        Returns an empty list for playlists not seen during training (cold-start).
        In the HybridRecommender pipeline, content-based recommendations provide
        coverage for cold-start playlists via _get_candidate_songs().

        Args:
            playlist_id: Database ID of the playlist.
            n_recommendations: Maximum number of results to return. Defaults to 10.

        Returns:
            List of (song_id, score) tuples sorted by descending score.
            Scores are sigmoid outputs in (0, 1), representing interaction probability.
        """
        if not self.model:
            if not self.load_model():
                logger.warning("No trained model available for recommendations")
                return []

        if playlist_id not in self.playlist_encoder:
            logger.info(
                "Playlist %d not in training data — cold-start, skipping collaborative scores",
                playlist_id,
            )
            return []

        playlist_idx = self.playlist_encoder[playlist_id]
        playlist = Playlist.objects.get(id=playlist_id)
        existing_song_ids = set(playlist.songs.values_list('id', flat=True))

        n_songs = len(self.song_encoder)
        all_song_indices = np.arange(n_songs)
        playlist_indices = np.full(n_songs, playlist_idx)

        predictions = self.model.predict(
            [playlist_indices, all_song_indices], batch_size=1024, verbose=0
        )
        predictions = predictions.flatten()

        song_scores = []
        for song_idx, score in enumerate(predictions):
            if song_idx in self.song_decoder:
                song_id = self.song_decoder[song_idx]
                if song_id not in existing_song_ids:
                    song_scores.append((song_id, float(score)))

        song_scores.sort(key=lambda x: x[1], reverse=True)
        return song_scores[:n_recommendations]

    def update_playlist_recommendations(
        self, playlist_id: int, n_recommendations: int = 10
    ) -> None:
        """Recompute and persist collaborative filtering recommendations for a playlist.

        Args:
            playlist_id: Database ID of the playlist.
            n_recommendations: Number of recommendations to store. Defaults to 10.
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
                    created_at=timezone.now(),
                )
            except Song.DoesNotExist:
                logger.warning("Song %d does not exist, skipping", song_id)

    def update_all_recommendations(self, n_recommendations: int = 10) -> None:
        """Recompute and persist recommendations for every playlist in the database.

        Args:
            n_recommendations: Recommendations per playlist. Defaults to 10.
        """
        playlists = Playlist.objects.all()
        for playlist in playlists:
            self.update_playlist_recommendations(playlist.id, n_recommendations)
            logger.info("Updated recommendations for playlist %d", playlist.id)
