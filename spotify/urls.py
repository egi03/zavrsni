from django.urls import path
from . import views

app_name = 'spotify'

urlpatterns = [
    path('connect/', views.connect_spotify, name='connect'),
    path('callback/', views.spotify_callback, name='callback'),
    path('import/', views.import_playlists, name='import_playlists'),
    path('import/<str:playlist_id>/', views.import_playlist, name='import_playlist'),
    path('disconnect/', views.disconnect_spotify, name='disconnect'),
    path('status/', views.spotify_status, name='status'),
]