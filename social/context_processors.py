from django.db.models import Q, Count
from .models import Notification, Message

def social_context(request):
    context = {
        'unread_messages_count': 0,
        'unread_notifications_count': 0,
    }
    
    if request.user.is_authenticated:
        context['unread_notifications_count'] = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        context['unread_messages_count'] = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
    
    return context