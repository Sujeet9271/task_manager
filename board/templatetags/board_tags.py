from django import template
from django.urls import reverse
from django.utils.html import mark_safe
import re

from accounts.models import Users
from board.models import Board, Column, Task
from task_manager.logger import logger
from task_manager.utils import get_full_url

register = template.Library()

@register.filter
def highlight_mentions(comment_text):
    """
    Highlight mentions in the comment and convert them to clickable links.
    """
    # Regular expression to find @mentions
    mention_pattern = r'@([a-zA-Z0-9_]+)'
    
    def replace_with_link(match):
        username = match.group(1)
        # Create a link to the user's profile page (adjust URL pattern if needed)
        url = "#"
        return f'<a href="{url}" class="mention">@{username}</a>'

    # Replace mentions with links and highlight them
    highlighted_comment = re.sub(mention_pattern, replace_with_link, comment_text)
    return mark_safe(highlighted_comment)

@register.filter
def notification_title(notification_title:str):
    return " ".join(notification_title.capitalize().split('_'))

@register.filter
def notification_trim(notification_text:str):
    words = notification_text.split(' ')[:10]
    return f"{" ".join(words)}..."


@register.filter
def get_tasks_for_user(column:Column, user:Users):
    return column.get_tasks(user)

@register.simple_tag
def get_board_full_url(board:Board, request):
    """Generate the full URL for the board view."""
    return get_full_url('board:board-view', args=[board.id])



@register.filter
def capitalize(value:str):
    return value.replace('_', ' ').title()


@register.filter(name='split')
def split(value, key): 
    if value:
        return value.split(key)
    return []


@register.filter(name="assigned_users")
def assigned_users(task:Task):
    return task.assigned_to.all()[0:2] if task.assigned_to.exists() else [task.created_by]

@register.filter
def initials(value:str):
    short_name = []
    logger.debug(f'{value=}')
    for part in value.split(' '):
        logger.debug(f'{part=}')
        if part:
            short_name.append(part[0].capitalize())
    return ''.join(short_name[:1])
