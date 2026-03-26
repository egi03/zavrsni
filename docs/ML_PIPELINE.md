# ML Pipeline — Music Recommendation System

This document explains the machine learning architecture in detail. For setup instructions see the main [README](../README.md).

---

## Overview

The system uses a **three-layer hybrid recommendation pipeline**:

```
Playlist (≥3 songs)
        │
        ▼
┌───────────────────────────────────────────┐
│          Candidate Generation             │
│  ┌──────────────┐  ┌──────────────────┐  │
│  │ Collaborative│  │  Content-Based   │  │
│  │  Filtering   │  │   (Tag + API)    │  │
│  └──────────────┘  └──────────────────┘  │
│         Popularity Fallback (cold-start)  │
└───────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────┐
│           Score Computation               │
│  collaborative_score × weight_1           │
│  + content_tag_score × weight_2           │
│  + content_similar_score × weight_3       │
│  + popularity_score × weight_4            │
└───────────────────────────────────────────┘
        │ Strategy weights (balanced/discovery/popular)
        ▼
   Ranked Recommendations
        │
        ▼
   User Feedback → RecommendationFeedback table
   (future retraining signal)
```

---

## 1. Neural Collaborative Filtering

**File:** `recommendations/collaborative_recommender.py`
**Class:** `PlaylistRecommender`

### Why collaborative filtering?

Collaborative filtering captures *implicit* user preferences — the fact that a playlist contains certain songs together reveals taste patterns that neither audio features nor genre tags can express. Two playlists containing both post-rock and jazz fusion belong in the same latent neighbourhood.

### Model Architecture

```
Playlist ID ──→ Embedding(n_playlists, 50) ──→ Flatten ──┐
                                                           │
                                                        Dot ──→ Add ──→ Sigmoid ──→ [0,1]
                                                           │
Song ID ─────→ Embedding(n_songs, 50) ───→ Flatten ──┘   │
                                                           │
Playlist Bias ─→ Embedding(n_playlists, 1) ──→ Flatten ──┤
Song Bias ─────→ Embedding(n_songs, 1) ──────→ Flatten ──┘
```

- **Embedding dimensions:** 50 (configurable via `RECOMMENDATION_SETTINGS['COLLABORATIVE_FACTORS']`)
- **L2 regularization:** 1e-5 on embedding weights — prevents overfitting on sparse data
- **Output activation:** Sigmoid — appropriate for binary implicit feedback (0/1)
- **Loss:** Binary cross-entropy with negative sampling

### Training Data

| Component | Detail |
|-----------|--------|
| Positive examples | All (playlist, song) pairs in the database — label=1 |
| Negative examples | Songs NOT in a playlist, sampled at 4:1 ratio — label=0 |
| Negative sampling ratio | 4 negatives per positive (standard for NCF, He et al. 2017) |
| Validation split | 10% held out during training |

**Why negative sampling?** The interaction matrix is extremely sparse — most songs are not in most playlists. Random negative samples force the model to discriminate between relevant and irrelevant songs rather than just predicting "1" everywhere.

### Training Callbacks

```python
EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, min_lr=1e-6)
```

- EarlyStopping prevents overfitting and makes epoch tuning unnecessary
- ReduceLROnPlateau adapts the learning rate when training plateaus

### Offline Evaluation Metrics

Computed via `train_with_evaluation()` with a 20% held-out split:

| Metric | Description |
|--------|-------------|
| **Precision@K** | Fraction of top-K recommendations that are held-out positives |
| **Recall@K** | Fraction of held-out positives recovered in top-K |
| **NDCG@K** | Normalised Discounted Cumulative Gain — rewards correct items ranked higher |

Run via: `python manage.py evaluate_model --retrain --k 10`

### Cold-Start Handling

New playlists not seen during training return an empty list from the collaborative component. The hybrid pipeline handles this gracefully — content-based and popularity scores still produce recommendations, just without collaborative signal.

---

## 2. Content-Based Filtering

**File:** `recommendations/content_recommender.py`
**Class:** `LastFMContentRecommender`

### Why Last.fm tags?

Audio features (tempo, energy, danceability) capture *acoustics* but miss genre and mood. Last.fm tags like `"post-rock"`, `"instrumental"`, `"melancholic"` encode semantic meaning that audio features cannot — two acoustically similar songs may belong to completely different genres.

### A) Tag-Based Similarity

**Pipeline:**

```
1. Build playlist tag profile
   For each song in playlist:
     - Fetch Last.fm tags if missing or >30 days stale
     - Accumulate tag weights with frequency boost

   avg_weight = Σ(tag_weight) / n_songs
   frequency_boost = min(tag_count / n_songs, 1.0)
   profile[tag] = avg_weight × (0.7 + 0.3 × frequency_boost)
   → Normalise to sum=1, keep top 20 tags

2. Score each candidate song
   For each matching tag:
     tag_similarity = min(song_weight, playlist_weight) / max(song_weight, playlist_weight)
     contribution = tag_similarity × playlist_weight × genre_boost_factor

   If < 2 matching tags → similarity × 0.5 (sparse match penalty)

3. Blend with popularity
   final_score = similarity × 0.8 + lastfm_listeners_normalized × 0.2
```

**Genre boost factors** (tuned to avoid over-recommendation of mainstream genres):

| Genre | Boost |
|-------|-------|
| classical | 1.4× |
| jazz, indie, folk, metal | 1.3× |
| rock, electronic, alternative, hip hop | 1.2× |
| pop | 1.1× |

### B) API-Based Similarity (Last.fm `track.getSimilar`)

For each song in the playlist (up to 10 seeds):
```
1. Call Last.fm track.getSimilar → returns ranked similar tracks
2. Score = position_score × match_score
   position_score = 1.0 - (position / total_results)
   match_score = Last.fm similarity float [0, 1]
3. Aggregate scores across all seeds
4. Look up aggregated tracks in local DB
5. Normalise by total score count
```

This method retrieves tracks the Last.fm community considers musically similar — complementary to tag matching.

### C) Ensemble

```python
combined_score = tag_score × 0.6 + api_score × 0.4
```

If a song appears in both methods, scores are averaged with weighting rather than taking the maximum — this rewards tracks that multiple signals agree on.

---

## 3. Hybrid Recommender

**File:** `recommendations/hybrid_recommender.py`
**Class:** `HybridRecommender`

### Strategy Weights

| Component | balanced | discovery | popular |
|-----------|----------|-----------|---------|
| Collaborative | **0.40** | 0.20 | 0.10 |
| Content tags | 0.30 | **0.50** | 0.20 |
| Content similar | 0.20 | 0.20 | 0.10 |
| Popularity | 0.10 | 0.10 | **0.60** |

**Design rationale:**
- `balanced` — the default; equal weight to all signals
- `discovery` — content dominates; finds musically similar songs users haven't heard
- `popular` — useful for new users with sparse history; surfaces trending songs in playlist's genre

### Score Aggregation

```python
hybrid_score = Σ(component_score × strategy_weight)
hybrid_score = min(hybrid_score, 1.0)  # cap at 1.0
```

All component scores are normalised to [0, 1] before aggregation. The collaborative scores are max-normalised within each batch; tag/similarity/popularity scores are inherently bounded.

### Candidate Generation

The pipeline gathers candidates from multiple sources to ensure diversity:

```
1. Collaborative filtering (if model is trained)  → n_needed × 2 songs
2. Content tag recommendations                    → n_needed songs
3. Content API similarity                         → n_needed songs
4. Popularity fallback (if total < n_needed)      → fill remainder
   (popularity ≥ 70 OR lastfm_listeners ≥ 100k)

Total candidates capped at 3 × n_needed before scoring
```

---

## 4. Data Flow: End-to-End

```
User adds song to playlist
        │
        ▼
1. Spotify API → fetch track metadata + audio features
2. Last.fm API → enrich with tags, playcount, listener count
3. Song stored in DB (Song model)
4. M2M link created (playlist.songs.add(song))
5. Recommendation cache cleared for this playlist
        │
        ▼ (on recommendation request)
6. HybridRecommender.recommend_hybrid(playlist, strategy)
7. Results stored in HybridRecommendation table
8. Served from cache for 30 minutes
        │
        ▼ (on user action)
9. RecommendationFeedback.objects.create(action='added'|'skipped')
10. Feedback available for future retraining (not currently automated)
```

---

## 5. Catalog-Level Evaluation

**File:** `recommendations/evaluation.py`
**Command:** `python manage.py evaluate_model`

Three metrics computed without retraining (fast, runs on existing data):

### Coverage
```
coverage = recommended_songs / total_songs × 100
```
Low coverage indicates the recommender is stuck in a popularity bubble, failing to surface the long tail.

### Popularity Bias (ARP — Average Recommendation Popularity)
Compares Spotify popularity (0–100) and Last.fm listener counts of recommended songs vs. the catalog average. High bias means the recommender offers songs users could find on their own.

### Score Distribution
Distribution statistics (mean, std, percentiles) of hybrid scores per strategy. Score collapse (very low std) indicates one component dominates the weighted sum.

### User Acceptance Rate
```
acceptance_rate = added_feedback_count / total_recommendations × 100
```
Computed from the `RecommendationFeedback` table. Measures how often users actually add recommended songs to their playlists — the most direct signal of recommendation quality.

---

## 6. Key Design Decisions & Tradeoffs

| Decision | Rationale | Alternative Considered |
|----------|-----------|----------------------|
| Implicit feedback (binary 0/1) | Users don't rate songs; playlist membership is the signal | Explicit ratings would require a separate rating UI |
| TensorFlow for NCF | Demonstrates ML framework integration; embeddings are first-class | scikit-learn NMF is simpler but lacks neural flexibility |
| Last.fm tags over audio features for content | Tags encode genre/mood semantics that audio features miss | Pure audio similarity (cosine on feature vectors) |
| SQLite for development | Zero-config, portable for thesis demo | PostgreSQL for production |
| AJAX polling for messages | Simple, no infrastructure required | WebSockets would be lower latency but add operational complexity |
| Strategy pattern for hybrid weights | Easy to tune and explain; strategies are a visible UI feature | Single fixed weight vector |

---

## 7. Running the ML Pipeline

```bash
# Enrich songs with Last.fm metadata (run after adding songs)
make enrich
# or: python manage.py enrich_songs_lastfm --batch-size 50

# Train the collaborative filtering model
make train
# or: python manage.py train_recommendations

# Generate recommendations for all playlists
python manage.py update_recommendations --strategy balanced

# Evaluate model quality (fast, no retraining)
make evaluate
# or: python manage.py evaluate_model

# Evaluate with held-out ranking metrics (slow, retrains model)
python manage.py evaluate_model --retrain --k 10
```
