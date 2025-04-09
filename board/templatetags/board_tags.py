from django import template
from django.urls import reverse
from django.utils.html import mark_safe
import re

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
