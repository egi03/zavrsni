from django.contrib import admin
from .models import (
    UserFollow, PlaylistFollow, Activity, Notification,
    Conversation, Message, PlaylistComment
)

@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ['follower', 'following', 'created_at']
    list_filter = ['created_at']
    search_fields = ['follower__username', 'following__username']

@admin.register(PlaylistFollow)
class PlaylistFollowAdmin(admin.ModelAdmin):
    list_display = ['user', 'playlist', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'playlist__name']

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['user__username']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'sender', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['recipient__username', 'sender__username']

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'updated_at']
    filter_horizontal = ['participants']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'conversation', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['sender__username', 'content']

@admin.register(PlaylistComment)
class PlaylistCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'playlist', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'playlist__name', 'content']