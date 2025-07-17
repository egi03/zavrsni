from django import template

register = template.Library()

@register.filter
def get_other_participant(conversation, current_user):
    """Get the other participant in a conversation"""
    return conversation.participants.exclude(id=current_user.id).first()