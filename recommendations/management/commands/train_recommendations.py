from django.core.management.base import BaseCommand
from recommendations.collaborative_recommender import PlaylistRecommender
from recommendations.content_recommender import ContentBasedRecommender


class Command(BaseCommand):
    help = 'Train recommendation models'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            choices=['collaborative', 'content', 'all'],
            default='all',
            help='Which model to train'
        )
    
    def handle(self, *args, **options):
        model_type = options['model']
        
        if model_type in ['collaborative', 'all']:
            self.stdout.write('Training collaborative filtering model...')
            cf_recommender = PlaylistRecommender()
            history = cf_recommender.train()
            
            if history:
                self.stdout.write(
                    self.style.SUCCESS('Collaborative model trained successfully!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Failed to train collaborative model')
                )
        
        if model_type in ['content', 'all']:
            self.stdout.write('Training content-based model...')
            cb_recommender = ContentBasedRecommender()
            history = cb_recommender.train_autoencoder()
            
            if history:
                self.stdout.write(
                    self.style.SUCCESS('Content model trained successfully!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Failed to train content model')
                )