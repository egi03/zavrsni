from django.urls import path
from . import views

app_name = 'music'

urlpatterns = [
    path('', views.playlists, name='playlists'),
    path('create/', views.create_playlist, name='create_playlist'),
    path('<int:playlist_id>/', views.playlist_detail, name='playlist_detail'),
    path('<int:playlist_id>/delete/', views.delete_playlist, name='delete_playlist'),
    path('<int:playlist_id>/add/', views.add_to_playlist, name='add_to_playlist'),
    path('<int:playlist_id>/remove/<int:song_id>/', views.remove_from_playlist, name='remove_from_playlist'),
    path('search/', views.search_songs, name='search_songs'),
]