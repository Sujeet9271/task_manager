from notifications.utils import get_notifications


def notifications(request):
    context = {}
    if not request.htmx:
        if request.user.is_authenticated:
            context['unread_notification_count'] = request.user.notifications.filter(read=False).count()
            context = get_notifications(user=request.user,page_number=1, context=context)
        else:
            context['notifications'] = []
    return context