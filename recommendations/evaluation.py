"""
Offline evaluation utilities for the music recommendation system.

Two categories of metrics:

1. Ranking metrics (Precision@K, Recall@K, NDCG@K) — require a held-out test split,
   computed inside PlaylistRecommender.train_with_evaluation(). These are unbiased only
   when the model is trained without seeing the test interactions.

2. Catalog-level metrics — computed from existing HybridRecommendation rows, no retraining
   needed. Run with `make evaluate` or `python manage.py evaluate_model`.
       - coverage: what fraction of the song catalog ever appears in recommendations
       - popularity_bias: are recommendations skewed toward already-popular songs?
       - score_distribution: distribution of hybrid scores per strategy
"""

import logging
from typing import Any, Dict

import numpy as np

logger = logging.getLogger(__name__)


def compute_catalog_coverage(strategy: str = 'balanced') -> Dict[str, Any]:
    """Compute the fraction of the song catalog that appears in at least one recommendation.

    Low coverage indicates the recommender is over-fitting to a small subset of popular
    items and failing to surface the long tail.

    Args:
        strategy: Recommendation strategy to evaluate. Defaults to 'balanced'.

    Returns:
        Dict with total_songs, recommended_songs, coverage_pct, unrecommended_count,
        and strategy.
    """
    from music.models import Song
    from recommendations.models import HybridRecommendation

    total_songs = Song.objects.count()
    recommended_count = (
        HybridRecommendation.objects.filter(strategy=strategy)
        .values('song_id')
        .distinct()
        .count()
    )

    return {
        'strategy': strategy,
        'total_songs': total_songs,
        'recommended_songs': recommended_count,
        'coverage_pct': round(recommended_count / total_songs * 100, 2) if total_songs > 0 else 0.0,
        'unrecommended_count': total_songs - recommended_count,
    }


def compute_popularity_bias(strategy: str = 'balanced') -> Dict[str, Any]:
    """Compute ARP (Average Recommendation Popularity) to detect popularity bias.

    Compares Spotify popularity and Last.fm listener counts for recommended songs.
    A high mean popularity relative to the catalog mean indicates popularity bias —
    the system over-recommends songs users would have found without a recommender.

    Args:
        strategy: Recommendation strategy to evaluate. Defaults to 'balanced'.

    Returns:
        Dict with per-field distribution statistics (mean, median, p25, p75).
    """
    from recommendations.models import HybridRecommendation

    recs = list(
        HybridRecommendation.objects.filter(strategy=strategy)
        .select_related('song')
        .values_list('song__popularity', 'song__lastfm_listeners')
    )

    popularities = [p for p, _ in recs if p is not None]
    listeners_m = [l / 1_000_000 for _, l in recs if l is not None]

    def _stats(values: list) -> Dict[str, float]:
        if not values:
            return {'mean': 0.0, 'median': 0.0, 'p25': 0.0, 'p75': 0.0}
        arr = np.array(values)
        return {
            'mean': round(float(np.mean(arr)), 3),
            'median': round(float(np.median(arr)), 3),
            'p25': round(float(np.percentile(arr, 25)), 3),
            'p75': round(float(np.percentile(arr, 75)), 3),
        }

    return {
        'strategy': strategy,
        'n_recommendations': len(recs),
        'spotify_popularity': _stats(popularities),
        'lastfm_listeners_millions': _stats(listeners_m),
    }


def compute_score_distribution(strategy: str = 'balanced') -> Dict[str, Any]:
    """Compute descriptive statistics of hybrid recommendation scores.

    Useful for detecting score collapse (all scores bunched near one value),
    which indicates the weighting scheme is dominated by a single component.

    Args:
        strategy: Recommendation strategy to evaluate. Defaults to 'balanced'.

    Returns:
        Dict with n, mean, std, min, p25, median, p75, max for the strategy's scores.
    """
    from recommendations.models import HybridRecommendation

    scores = list(
        HybridRecommendation.objects.filter(strategy=strategy)
        .values_list('hybrid_score', flat=True)
    )

    if not scores:
        return {'strategy': strategy, 'n': 0}

    arr = np.array(scores)
    return {
        'strategy': strategy,
        'n': len(arr),
        'mean': round(float(np.mean(arr)), 4),
        'std': round(float(np.std(arr)), 4),
        'min': round(float(np.min(arr)), 4),
        'p25': round(float(np.percentile(arr, 25)), 4),
        'median': round(float(np.median(arr)), 4),
        'p75': round(float(np.percentile(arr, 75)), 4),
        'max': round(float(np.max(arr)), 4),
    }


def compute_user_acceptance_rate(strategy: str = 'balanced') -> Dict[str, Any]:
    """Compute the fraction of recommendations that users actually added to their playlists.

    This is the most direct offline proxy for recommendation quality — it measures
    whether users found the suggestions useful enough to act on.

    Args:
        strategy: Recommendation strategy to evaluate. Defaults to 'balanced'.

    Returns:
        Dict with total_recommendations, accepted_count, acceptance_rate_pct, and strategy.
    """
    from recommendations.models import HybridRecommendation, RecommendationFeedback

    total = HybridRecommendation.objects.filter(strategy=strategy).count()
    accepted = RecommendationFeedback.objects.filter(
        recommendation__strategy=strategy,
        action='added',
    ).count()

    return {
        'strategy': strategy,
        'total_recommendations': total,
        'accepted_count': accepted,
        'acceptance_rate_pct': round(accepted / total * 100, 2) if total > 0 else 0.0,
    }


def run_full_evaluation() -> Dict[str, Dict[str, Any]]:
    """Run all catalog-level metrics for all recommendation strategies.

    Returns:
        Nested dict keyed by strategy → metric_type → result dict.
    """
    strategies = ['balanced', 'discovery', 'popular']
    results: Dict[str, Dict[str, Any]] = {}

    for strategy in strategies:
        results[strategy] = {
            'coverage': compute_catalog_coverage(strategy),
            'popularity_bias': compute_popularity_bias(strategy),
            'score_distribution': compute_score_distribution(strategy),
            'user_acceptance': compute_user_acceptance_rate(strategy),
        }
        logger.info(
            "Evaluated strategy '%s': coverage=%.1f%%, acceptance=%.1f%%",
            strategy,
            results[strategy]['coverage']['coverage_pct'],
            results[strategy]['user_acceptance']['acceptance_rate_pct'],
        )

    return results
