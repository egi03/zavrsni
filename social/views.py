from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
import json
from .models import (
    UserFollow, PlaylistFollow, Activity, Notification,
    Conversation, Message, PlaylistComment
)
from music.models import Playlist, Song
from accounts.models import UserProfile


@login_required
def social_feed(request):
    following_users = request.user.following.values_list('following_id', flat=True)
    
    activities = Activity.objects.filter(
        Q(user__in=following_users) | Q(user=request.user)
        ).select_related('user', 'playlist', 'song', 'target_user').prefetch_related(
            'user__userprofile')[:50]


    popular_users = User.objects.exclude(
        Q(id=request.user.id) | Q(followers__follower=request.user)
    ).annotate(
        followers_count=Count('followers'),
        playlist_count=Count('playlists')
    ).filter(playlist_count__gt=0).order_by('-followers_count')[:5]
    
    
    trending_playlists = Playlist.objects.filter(
        is_public=True
    ).annotate(
        followers_count=Count('playlist_followers'),
        recent_activity=Count('activities', filter=Q(activities__created_at__gte=timezone.now() - timezone.timedelta(days=7)))
    ).order_by('-recent_activity', '-followers_count')[:5]
    
    
    return render(request, 'social/feed.html', {
        'activities': activities,
        'popular_users': popular_users,
        'trending_playlists': trending_playlists
    })

@login_required
@require_POST
def follow_user(request, username):
    if not username or not username.strip():
        return JsonResponse({'error': 'Invalid username'}, status=400)
    
    user_to_follow = get_object_or_404(User, username=username)
    
    if not user_to_follow.username or not user_to_follow.username.strip():
        return JsonResponse({'error': 'Invalid user account'}, status=400)
    
    if user_to_follow == request.user:
        return JsonResponse({'error': 'Ne možeš zapratiti samog sebe'}, status=400)
    
    if not request.user.username or not request.user.username.strip():
        return JsonResponse({'error': 'Your account has invalid username'}, status=400)
    
    follow, created = UserFollow.objects.get_or_create(
        follower=request.user,
        following=user_to_follow
    )
    
    if not created:
        follow.delete()
        following = False
        message = f'Prestali ste pratiti {username}'
    else:
        following = True
        message = f'Zapratili ste {username}'
        
        Notification.objects.create(
            recipient=user_to_follow,
            sender=request.user,
            notification_type='follow',
            message=f'{request.user.username} vas je počeo pratiti'
        )
        
        Activity.objects.create(
            user=request.user,
            activity_type='user_followed',
            target_user=user_to_follow
        )
    
    followers_count = user_to_follow.followers.count()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'following': following,
            'followers_count': followers_count,
            'message': message,
            'message_type': 'success'
        })
    
    messages.success(request, message)
    return redirect('accounts:profile_view', username=username)

@login_required
@require_POST
def follow_playlist(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id)
    
    if not playlist.is_public and playlist.user != request.user:
        return JsonResponse({'error': 'Nije moguce pratiti privatnu playlistu'}, status=403)
    
    follow, created = PlaylistFollow.objects.get_or_create(
        user=request.user,
        playlist=playlist
    )
    
    if not created:
        follow.delete()
        following = False
    else:
        following = True
        
        if playlist.user != request.user:
            Notification.objects.create(
                recipient=playlist.user,
                sender=request.user,
                notification_type='playlist_follow',
                playlist=playlist,
                message=f'{request.user.username} zapratio je vašu playlistu "{playlist.name}"'
            )
        
        Activity.objects.create(
            user=request.user,
            activity_type='playlist_followed',
            playlist=playlist
        )
        
    followers_count = playlist.playlist_followers.count()
    
    return JsonResponse({
        'following': following,
        'followers_count': followers_count
    })

@login_required
@require_POST
def start_conversation(request, username):
    """Start a conversation with a user without sending a message"""
    recipient = get_object_or_404(User, username=username)
    
    if recipient == request.user:
        return JsonResponse({'error': 'Ne možete pokrenuti razgovor sa samim sobom'}, status=400)
    
    conversation = Conversation.objects.filter(
        participants=request.user
    ).filter(
        participants=recipient
    ).distinct().first()
    
    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, recipient)
    
    return JsonResponse({
        'success': True,
        'conversation_id': conversation.id,
        'redirect_url': f'/social/messages/conversation/{conversation.id}/'
    })
    
@login_required
def messages_view(request):
    conversations = request.user.conversations.annotate(
        last_message_time=Count('messages')
    ).prefetch_related(
        Prefetch('messages', queryset=Message.objects.select_related('sender'))
    ).order_by('-updated_at')
    
    return render(request, 'social/messages.html', {'conversations': conversations})

@login_required
def conversation_view(request, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.prefetch_related('participants'),
        id=conversation_id,
        participants=request.user
    )
    
    conversation.messages.filter(
        ~Q(sender=request.user),
        is_read=False
    ).update(is_read=True)
    
    messages = conversation.messages.select_related(
        'sender', 'shared_playlist', 'shared_song'
    ).order_by('created_at')
    
    other_participant = conversation.get_other_participant(request.user)
    
    context = {
        'conversation': conversation,
        'messages': messages,
        'other_participant': other_participant
    }
    
    return render(request, 'social/conversation.html', context)

@login_required
@require_POST
def send_message(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)
    content = data.get('content', '').strip()
    conversation_id = data.get('conversation_id')
    recipient_username = data.get('recipient')

    if not content:
        return JsonResponse({'error': 'Poruka ne moze biti prazna'}, status=400) 
    
    if conversation_id:
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=request.user
        )
    elif recipient_username:
        recipient = get_object_or_404(User, username=recipient_username)
        if recipient == request.user:
            return JsonResponse({'error': 'Ne moze poruka samom sebi'}, status=400)
        
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=recipient
        ).distinct().first()
        
        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, recipient)
            
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)

    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content
    )
    
    return JsonResponse({
        'success': True,
        'message': {
            'id': message.id,
            'content': message.content,
            'sender': message.sender.username,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M')
        }
    })

@login_required
def notifications_view(request):
    notifications = request.user.notifications.select_related(
        'sender', 'playlist'
    )
    
    if request.GET.get('mark_read'):
        notifications.filter(is_read=False).update(is_read=True)
    
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page', 1)
    notifications_page = paginator.get_page(page)
    
    context = {
        'notifications': notifications_page,
        'unread_count': notifications.filter(is_read=False).count()
    }
    
    return render(request, 'social/notifications.html', context)

@login_required
@require_POST
def add_comment(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id)
    
    if not playlist.is_public and playlist.user != request.user:
        return JsonResponse({'error': 'Ne moze se komentirati privatne playliste'}, status=403)
    
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)
    content = data.get('content', '').strip()
    parent_id = data.get('parent_id')
    
    if not content:
        return JsonResponse({'error': 'Komentar ne moze biti prazan'}, status=400)
    
    comment = PlaylistComment.objects.create(
        user=request.user,
        playlist=playlist,
        content=content,
        parent_id=parent_id if parent_id else None
    )
    
    if playlist.user != request.user:
        Notification.objects.create(
            recipient=playlist.user,
            sender=request.user,
            notification_type='comment',
            playlist=playlist,
            message=f'{request.user.username} komentirao je vašu playlistu'
        )
        
    return JsonResponse({
        'success': True,
        'comment': {
            'id': comment.id,
            'user': comment.user.username,
            'content': comment.content,
            'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M')
        }
    })

@login_required
def followers_list(request, username):
    user = get_object_or_404(User, username=username)
    followers = UserFollow.objects.filter(
        following=user,
        follower__username__isnull=False,
        follower__username__gt=''
    ).select_related('follower', 'follower__userprofile')
    
    current_user_following = set()
    if request.user.is_authenticated:
        current_user_following = set(
            UserFollow.objects.filter(
                follower=request.user,
                following__username__isnull=False,
                following__username__gt=''
            ).values_list('following__username', flat=True)
        )
    
    context = {
        'profile_user': user,
        'followers': followers,
        'current_user_following': current_user_following,
        'is_followers': True
    }
    
    return render(request, 'social/follow_list.html', context)

@login_required
def following_list(request, username):
    user = get_object_or_404(User, username=username)
    following = UserFollow.objects.filter(
        follower=user,
        following__username__isnull=False,
        following__username__gt=''
    ).select_related('following', 'following__userprofile')
    
    current_user_following = set()
    if request.user.is_authenticated:
        current_user_following = set(
            UserFollow.objects.filter(
                follower=request.user,
                following__username__isnull=False,
                following__username__gt=''
            ).values_list('following__username', flat=True)
        )
    
    context = {
        'profile_user': user,
        'following': following,
        'current_user_following': current_user_following,
        'is_followers': False
    }
    
    return render(request, 'social/follow_list.html', context)


@login_required
def poll_messages(request, conversation_id):
    last_id = request.GET.get('last_id', 0)
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        participants=request.user
    )
    
    messages = conversation.messages.filter(id__gt=last_id).select_related(
        'sender', 'shared_playlist', 'shared_song'
    ).order_by('created_at')
    
    messages_data = [
        {
            'id': msg.id,
            'sender': msg.sender.username,
            'sender_avatar': msg.sender.userprofile.profile_picture.url if msg.sender.userprofile.profile_picture else None,
            'content': msg.content,
            'time': msg.created_at.strftime('%H:%M'),
        } for msg in messages
    ]
    
    return JsonResponse({'messages': messages_data})