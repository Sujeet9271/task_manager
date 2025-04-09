from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.core.paginator import Paginator
from django.db.models import QuerySet

from notifications.models import Notification

from task_manager.logger import logger

# Create your views here.
@require_GET
@login_required
def notifications(request):
    context={}
    notifications:QuerySet[Notification] = request.user.notifications.all()
    try:
        paginator = Paginator(notifications,1)
        page_number = int(request.GET.get('page',1))
        page_obj = paginator.get_page(page_number)
        context['notifications'] = page_obj.object_list
        if page_obj.has_next():
            notifications = reverse_lazy('notifications:notifications')
            context['next'] = f'{notifications}?page={page_number+1}'
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