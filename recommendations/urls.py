from django.urls import path
from . import views

app_name = 'recommendations'

urlpatterns = [
    path('playlist/<int:playlist_id>/', views.get_playlist_recommendations, name='playlist_recommendations'),
    path('playlist/<int:playlist_id>/song/<int:song_id>/explanation/', views.get_recommendation_explanation, name='recommendation_explanation'),
    path('feedback/<int:recommendation_id>/', views.record_recommendation_feedback, name='recommendation_feedback' ),
    path('stats/', views.get_recommendation_stats, name='recommendation_stats'),
]