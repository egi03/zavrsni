from django.core.management.base import BaseCommand
from django.db.models import Q
from music.models import Song
from lastfm.utils import batch_enrich_songs_with_lastfm
import time


class Command(BaseCommand):
    help = 'Enrich songs with Last.fm data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of songs to enrich in a batch'
        )
        parser.add_argument(
            '--playlist-id',
            type=int,
            help='Only enrich songs from playlist with id'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update every song'
        )
    
    def handle(self, *args, **options):
        batch_size = options['batch_size']
        playlist_id = options.get('playlist_id')
        force_update = options.get('force', False)
        
        if playlist_id:
            from music.models import Playlist
            try:
                playlist = Playlist.objects.get(id=playlist_id)
                songs = playlist.songs.all()
                self.stdout.write(f'Enriching songs from playlist: {playlist.name}')
            except Playlist.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Playlist {playlist_id} not found'))
                return
        else:
            if force_update:
                songs = Song.objects.all()
            else:
                songs = Song.objects.filter(
                    Q(lastfm_tags={}) | Q(lastfm_tags__isnull=True)
                )
        
        total_songs = songs.count()
        self.stdout.write(f'Total songs: {total_songs}')
        
        processed = 0
        enriched = 0
        
        for i in range(0, total_songs, batch_size):
            batch = list(songs[i:i+batch_size])
            self.stdout.write(f'\Batch: {i//batch_size + 1} ({i+1}-{min(i+batch_size, total_songs)} of {total_songs})')
            
            batch_enriched = batch_enrich_songs_with_lastfm(batch)
            enriched += batch_enriched
            processed += len(batch)
            
            self.stdout.write(f'Enriched {batch_enriched} / {len(batch)}')
            
            if i + batch_size < total_songs:
                self.stdout.write('Wait 2 secondes')
                time.sleep(2)
        
        self.stdout.write(self.style.SUCCESS('\nDONE'))
        
        songs_with_tags = Song.objects.exclude(lastfm_tags={}).count()
        self.stdout.write(f'\nTotal songs with Last.fm tags: {songs_with_tags}')