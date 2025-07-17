from django.urls import path
from . import views

app_name = 'social'

urlpatterns = [
    path('feed/', views.social_feed, name='feed'),
    
    path('follow/user/<str:username>/', views.follow_user, name='follow_user'),
    path('follow/playlist/<int:playlist_id>/', views.follow_playlist, name='follow_playlist'),
    path('followers/<str:username>/', views.followers_list, name='followers'),
    path('following/<str:username>/', views.following_list, name='following'),
    
    path('messages/', views.messages_view, name='messages'),
    path('messages/conversation/<int:conversation_id>/', views.conversation_view, name='conversation'),
    path('messages/send/', views.send_message, name='send_message'),
    path('messages/start/<str:username>/', views.start_conversation, name='start_conversation'),
    
    path('notifications/', views.notifications_view, name='notifications'),
    
    path('playlist/<int:playlist_id>/comment/', views.add_comment, name='add_comment'),
    
    path('messages/poll/<int:conversation_id>/', views.poll_messages, name='poll_messages'),
]