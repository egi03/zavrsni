from django.core.management.base import BaseCommand
from music.models import Playlist
from recommendations.hybrid_recommender import HybridRecommender


class Command(BaseCommand):
    help = 'Update recommendations for playlists'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--playlist-id',
            type=int,
            help='Update specific playlist'
        )
        parser.add_argument(
            '--strategy',
            type=str,
            default='balanced',
            choices=['balanced', 'discovery', 'similarity', 'popular'],
            help='Recommendation strategy'
        )
    
    def handle(self, *args, **options):
        playlist_id = options.get('playlist_id')
        strategy = options['strategy']
        
        recommender = HybridRecommender()
        
        if playlist_id:
            playlists = Playlist.objects.filter(id=playlist_id)
        else:
            playlists = Playlist.objects.filter(songs__isnull=False).distinct()
        
        self.stdout.write(f'Updating {playlists.count()} playlists...')
        
        for playlist in playlists:
            try:
                recommender.update_hybrid_recommendations(
                    playlist.id,
                    strategy=strategy,
                    n_recommendations=20
                )
                self.stdout.write(f'Updated: {playlist.name}')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating {playlist.name}: {e}')
                )
        
        self.stdout.write(self.style.SUCCESS('Done!'))