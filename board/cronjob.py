from datetime import date
from django.contrib.contenttypes.models import ContentType
from board.models import Tag, Task
from notifications.models import Notification




def overdue_tasks():
    tasks = Task.objects.filter(due_date__lt=date.today(), is_complete=False)
    content_type = ContentType.objects.get_for_model(Task)  # Corrected ContentType import
    over_due_tag,_ = Tag.objects.get_or_create(name="overdue")
    notifications = []
    for task in tasks:
        if task.parent_task:
            message = (
                f"SubTask '{task.title}' (ID: {task.id}) assigned to you in the '{task.column.board.name}' "
                f"board and '{task.column.name}' column is overdue. The due date was {task.due_date}. "
                "Please review and take necessary action. This subtask is part of the main task "
                f"'{task.parent_task.title}' (ID: {task.parent_task.id})."
            )
        else:
            message = (
                f"Task '{task.title}' (ID: {task.id}) assigned to you in the '{task.column.board.name}' "
                f"board and '{task.column.name}' column is overdue. The due date was {task.due_date}. "
                "Please review and take necessary action."
            )

        for user in task.assigned_to.all():
            notification = Notification(
                notification_type='task_exceeded_due_date',  # Use keyword argument
                content_type=content_type,
                object_id=task.id,  # Assuming task is the content object
                content_object=task,
                message=message,
                user=user
            )
            # If users is a ManyToManyField, you can use `add()` after saving or set() if using bulk_create
            notifications.append(notification)

    # Bulk create notifications
    Notification.objects.bulk_create(notifications, batch_size=1000)
    over_due_tag.tasks.add(*tasks)

