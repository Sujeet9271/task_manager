from decimal import Decimal
from django.db.models.signals import post_save, pre_save, m2m_changed, post_delete
from django.forms.models import model_to_dict

from django.dispatch import receiver
from board.models import Board, Column, Task, Comments, TaskHistory
from notifications.models import Notification
from task_manager.logger import logger
from accounts.models import Users
import hashlib
import json

from datetime import datetime,date


@receiver(m2m_changed, sender=Board.members.through)
def create_board_member_notification(sender, instance: Board, action, reverse, model, pk_set, **kwargs):
    """Signal handler to create notifications when users are added or removed from a board."""
    logger.info(f'{action=}, {sender=}, {model=}, {instance=}, {pk_set=}')
    if instance.created_by_id in pk_set:
        return
    
    if action == 'post_add':  # Users are added
        message = f"Welcome! You've been added to the board: '{instance.name}' of the workspace: '{instance.workspace.name}'. Stay tuned for updates and tasks."
        Notification.create_notification(pk_set, 'assigned_to_board', instance, message)
    
    elif action in ['post_remove', 'post_clear']:  # Users are removed
        message = f"You've been removed from the board: '{instance.name}'. You will no longer receive updates for this board."
        Notification.create_notification(pk_set, 'removed_from_board', instance, message)


@receiver(m2m_changed, sender=Task.assigned_to.through)
def create_task_member_notification(sender, instance: Task, action, reverse, model, pk_set, **kwargs):
    """Signal handler to create notifications when users are added or removed from a task."""
    logger.info(f'{action=}, {sender=}, {model=}, {instance=}, {pk_set=}')
    if instance.created_by_id in pk_set:
        return
    if action == 'post_add':  # Users are added            
        if instance.due_date:
            message = f"You've been assigned to the task: '{instance.title}' (ID: {instance.id}) in the board: '{instance.column.board.name}'. The task is due on {instance.due_date}. Please make sure to complete it on time."
        else:
            message = f"You've been assigned to the task: '{instance.title}' (ID: {instance.id}) in the board: '{instance.column.board.name}'. There is no due date set for this task. Please review and start working on it."
        
        Notification.create_notification(pk_set, 'assigned_to_task', instance, message)
    
    elif action in ['post_remove', 'post_clear']:  # Users are removed
        message = f"You've been removed from the task: '{instance.title}' (ID: {instance.id}) in the board: '{instance.column.board.name}'."
        Notification.create_notification(pk_set, 'removed_from_task', instance, message)

@receiver(m2m_changed, sender=Comments.mentioned_users.through)
def create_task_member_notification(sender, instance: Comments, action, reverse, model, pk_set, **kwargs):
    """Signal handler to create notifications when users are mentioned in a comment."""
    logger.info(f'{action=}, {sender=}, {model=}, {instance=}, {pk_set=}')
    
    if action == 'post_add':  # Users are added
        message = f"You've been mentioned in a comment for task: '{instance.task.title}' (ID: {instance.task.id}). Check the comment to see what's being discussed!"
        Notification.create_notification(pk_set, 'mentioned_in_comment', instance, message)



class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        logger.info(f'{obj=}')
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return str(obj)
        # Add more custom type handlers here
        return super().default(obj)

def clean_for_json(data):
    if isinstance(data, dict):
        return {k: clean_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_for_json(i) for i in data]
    elif isinstance(data, (date, datetime)):
        return data.isoformat()
    elif isinstance(data, Decimal):
        return float(data)
    return data

@receiver(pre_save, sender=Task)
def pre_save_task(sender, instance: Task, *args, **kwargs):
    if not instance.pk and instance.created_by:
        instance.updated_by = instance.created_by

def generate_hash(data):
    json_data = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_data.encode('utf-8')).hexdigest()

@receiver(post_save, sender=Task)
def post_save_task(sender, instance: Task, created: bool, **kwargs):
    logger.info('post_save_task triggered for Task ID %s', instance.id)

    # Convert instance to dict and clean it
    current_data = model_to_dict(instance, exclude=['id', 'created_at', 'updated_at'])
    current_data['assigned_to'] = list(instance.assigned_to.values_list('id', flat=True))
    current_data = clean_for_json(current_data)

    current_hash = generate_hash(current_data)
    latest_history = TaskHistory.objects.filter(task=instance).order_by('-id').first()

    if created or not latest_history:
        TaskHistory.objects.create(
            task=instance,
            updated_by=instance.updated_by,
            changes=current_data,
            snapshot=current_data,
            hash=current_hash
        )
        return

    if latest_history.hash == current_hash:
        logger.info("No changes detected for Task ID %s", instance.id)
        return

    previous_data = clean_for_json(latest_history.snapshot)
    diff = {}

    for key, new_val in current_data.items():
        old_val = previous_data.get(key)
        if old_val != new_val:
            diff[key] = {
                'from': old_val,
                'to': new_val
            }

    if diff and current_hash!=latest_history.hash:
        TaskHistory.objects.create(
            task=instance,
            updated_by=instance.updated_by,
            changes=diff,
            snapshot=current_data,
            hash=current_hash
        )
