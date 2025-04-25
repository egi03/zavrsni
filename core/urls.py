from django.urls import path
from . import views



urlpatterns = [
    path('', views.homepage, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),

    path('playlists/', views.playlists, name='playlists'),
    path('playlists/create/', views.create_playlist, name='create_playlist'),
    path('playlists/<int:playlist_id>/', views.playlist_detail, name='playlist_detail'),
    
    path('delete_playlist/<int:playlist_id>/', views.delete_playlist, name='delete_playlist'),
    path('add_to_playlist/<int:playlist_id>/', views.add_to_playlist, name='add_to_playlist'),
    path('search_songs/', views.search_songs, name='search_songs'),
    path('remove_from_playlist/<int:playlist_id>/<int:song_id>/', views.remove_from_playlist, name='remove_from_playlist'),
]
