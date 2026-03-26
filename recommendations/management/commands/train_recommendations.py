"""Management command to train collaborative filtering recommendation models."""

from django.core.management.base import BaseCommand

from recommendations.collaborative_recommender import PlaylistRecommender


class Command(BaseCommand):
    """Train the collaborative filtering model.

    Uses binary cross-entropy with negative sampling (the correct objective for
    implicit feedback). EarlyStopping prevents overfitting without manual epoch tuning.
    Run `make train-eval` instead if you want Precision@K / Recall@K / NDCG@K metrics.
    """

    help = 'Train recommendation models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            choices=['collaborative', 'all'],
            default='all',
            help='Which model to train (default: all)',
        )
        parser.add_argument(
            '--neg-ratio', type=int, default=4,
            help='Negative samples per positive interaction (default: 4)',
        )

    def handle(self, *args, **options):
        model_type = options['model']

        if model_type in ['collaborative', 'all']:
            self.stdout.write('Training collaborative filtering model...')
            cf_recommender = PlaylistRecommender()
            history = cf_recommender.train(negative_sample_ratio=options['neg_ratio'])

            if history:
                epochs_run = len(history.history['loss'])
                final_val_loss = history.history['val_loss'][-1]
                final_val_auc = history.history.get('val_auc', [None])[-1]

                self.stdout.write(self.style.SUCCESS(
                    f'Collaborative model trained successfully! '
                    f'({epochs_run} epochs, val_loss={final_val_loss:.4f}'
                    + (f', val_auc={final_val_auc:.4f}' if final_val_auc is not None else '')
                    + ')'
                ))
                self.stdout.write(
                    self.style.NOTICE("Tip: run 'make evaluate' for catalog-level metrics")
                )
            else:
                self.stdout.write(self.style.ERROR('Failed to train collaborative model'))
