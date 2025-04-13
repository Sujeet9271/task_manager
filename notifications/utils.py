from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.urls import reverse_lazy

from notifications.models import Notification

from task_manager.logger import logger


def get_notifications(user, page_number=1, context:dict=dict):
    notifications:QuerySet[Notification] = user.notifications.all()
    try:
        paginator = Paginator(notifications,1)
        page_obj = paginator.get_page(page_number)
        context['notifications'] = page_obj.object_list
        if page_obj.has_next():
            notifications = reverse_lazy('notifications:notifications')
            context['next'] = f'{notifications}?page={page_number+1}'
    except Exception as e:
        logger.exception(stack_info=False, msg=str(e))
        context['notifications'] = []
    return context

