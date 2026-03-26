"""Management command to evaluate the recommendation system quality."""

from django.core.management.base import BaseCommand

from recommendations.collaborative_recommender import PlaylistRecommender
from recommendations.evaluation import run_full_evaluation


class Command(BaseCommand):
    """Evaluate recommendation quality metrics.

    Two modes:
      Default (fast): catalog-level metrics from existing recommendations —
        coverage, popularity bias, score distributions. No retraining needed.

      --retrain (slow): holds out test_fraction of interactions, retrains, then
        computes unbiased Precision@K, Recall@K, NDCG@K on the held-out set.
    """

    help = 'Evaluate recommendation model quality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--k', type=int, default=10,
            help='Ranking cutoff for Precision/Recall/NDCG (default: 10)',
        )
        parser.add_argument(
            '--test-fraction', type=float, default=0.2,
            help='Fraction of interactions to hold out for ranking evaluation (default: 0.2)',
        )
        parser.add_argument(
            '--retrain', action='store_true',
            help='Retrain with hold-out split to compute unbiased P@K / R@K / NDCG',
        )

    def handle(self, *args, **options):
        k = options['k']

        self.stdout.write(self.style.HTTP_INFO('\n── Catalog-level evaluation ──'))
        results = run_full_evaluation()

        for strategy, data in results.items():
            cov = data['coverage']
            dist = data['score_distribution']
            bias = data['popularity_bias']

            self.stdout.write(f'\n  Strategy: {strategy.upper()}')
            self.stdout.write(
                f"  Coverage:  {cov['recommended_songs']}/{cov['total_songs']} songs "
                f"({cov['coverage_pct']}%)"
            )

            if dist.get('n', 0) > 0:
                self.stdout.write(
                    f"  Scores:    mean={dist['mean']:.3f}  "
                    f"std={dist['std']:.3f}  "
                    f"median={dist['median']:.3f}  "
                    f"[{dist['min']:.3f}, {dist['max']:.3f}]"
                )

            sp = bias['spotify_popularity']
            if sp['mean'] > 0:
                self.stdout.write(
                    f"  Popularity bias (Spotify 0-100): "
                    f"mean={sp['mean']:.1f}  median={sp['median']:.1f}"
                )

        if options['retrain']:
            test_pct = int(options['test_fraction'] * 100)
            self.stdout.write(
                self.style.WARNING(
                    f'\n── Ranking evaluation (retraining with {test_pct}% hold-out, k={k}) ──'
                )
            )
            recommender = PlaylistRecommender()
            result = recommender.train_with_evaluation(
                test_fraction=options['test_fraction'],
                k=k,
            )

            if result is None:
                self.stdout.write(self.style.ERROR('  Insufficient data for evaluation'))
                return

            metrics = result['metrics']
            history = result['history']
            epochs_run = len(history.history['loss'])
            final_val_loss = history.history['val_loss'][-1]

            self.stdout.write(self.style.SUCCESS('\n  Ranking metrics:'))
            self.stdout.write(f"  Playlists evaluated: {metrics['n_test_playlists']}")
            self.stdout.write(f"  Precision@{k}:  {metrics[f'precision@{k}']:.4f}")
            self.stdout.write(f"  Recall@{k}:     {metrics[f'recall@{k}']:.4f}")
            self.stdout.write(f"  NDCG@{k}:       {metrics[f'ndcg@{k}']:.4f}")
            self.stdout.write(
                f"\n  Training: {epochs_run} epochs, "
                f"final val_loss={final_val_loss:.4f}"
            )
        else:
            self.stdout.write(
                self.style.NOTICE(
                    '\n  Tip: run with --retrain to compute Precision@K / Recall@K / NDCG@K'
                )
            )
