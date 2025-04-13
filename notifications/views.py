from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

from notifications.models import Notification

from notifications.utils import get_notifications
from task_manager.logger import logger



@require_GET
@login_required
def notifications(request):
    context={}
    try:
        page_number = int(request.GET.get('page',1))
        context = get_notifications(user=request.user, page_number=page_number, context=context)
    except Exception as e:
        logger.exception(stack_info=False, msg=str(e))
        context['notifications'] = []
    response = render(request,'notifications/notification_list.html',context)
    return response


@require_GET
@login_required
def read_notification(request,id):
    context={}
    notification:Notification = request.user.notifications.filter(id=id).first()
    if not notification.read:
        notification.read = True
        notification.save(update_fields=['read','updated_at'])
    context['notification'] = notification
    response = render(request,'notifications/notification_card.html',context)
    response['HX-Trigger'] = 'notificationRead'
    return response