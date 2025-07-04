from decimal import Decimal
from django.db.models.signals import post_save, pre_save, m2m_changed, post_delete
from django.forms.models import model_to_dict
from django.utils import timezone
from django.dispatch import receiver
from board.models import Board, Column, Task, Comments, TaskHistory
from notifications.models import Notification
from task_manager.logger import logger
from accounts.models import Users
import hashlib
import json

from datetime import datetime,date, timedelta


@receiver(m2m_changed, sender=Board.members.through)
def m2m_changes_board_members(sender, instance: Board, action, reverse, model, pk_set:set, **kwargs):
    """Signal handler to create notifications when users are added or removed from a board."""
    logger.info(f'm2m_changes_board_members, {action=}')
    
    if instance.created_by_id in pk_set:
        pk_set.remove(instance.created_by_id)
    
    if action == 'post_add':  # Users are added
        message = f"Welcome! You've been added to the board: '{instance.name}' of the workspace: '{instance.workspace.name}'. Stay tuned for updates and tasks."
        Notification.create_notification(pk_set, 'assigned_to_board', instance, message)
    
    elif action in ['post_remove', 'post_clear']:  # Users are removed
        message = f"You've been removed from the board: '{instance.name}'. You will no longer receive updates for this board."
        Notification.create_notification(pk_set, 'removed_from_board', instance, message)


@receiver(m2m_changed, sender=Task.assigned_to.through)
def m2m_changes_task_assigned_to(sender, instance: Task, action, reverse, model, pk_set:set, **kwargs):
    """Signal handler to create notifications when users are added or removed from a task."""
    logger.debug(f' m2m_changes_task_assigned_to, {action=}')
    if action == 'post_add':  # Users are added        
        if instance.created_by in pk_set:    
            pk_set.remove(instance.created_by_id)

        if instance.due_date:
            message = f"You've been assigned to the task: '{instance.title}' (ID: {instance.id}) in the board: '{instance.column.board.name}'. The task is due on {instance.due_date}. Please make sure to complete it on time."
        else:
            message = f"You've been assigned to the task: '{instance.title}' (ID: {instance.id}) in the board: '{instance.column.board.name}'. There is no due date set for this task. Please review and start working on it."
        
        Notification.create_notification(pk_set, 'assigned_to_task', instance, message)
        create_history(instance=instance)
    
    elif action in ['post_remove', 'post_clear']:  # Users are removed
        message = f"You've been removed from the task: '{instance.title}' (ID: {instance.id}) in the board: '{instance.column.board.name}'."
        Notification.create_notification(pk_set, 'removed_from_task', instance, message)
        create_history(instance=instance)

@receiver(m2m_changed, sender=Comments.mentioned_users.through)
def m2m_changed_comment_mentioned_users(sender, instance: Comments, action, reverse, model, pk_set, **kwargs):
    """Signal handler to create notifications when users are mentioned in a comment."""
    logger.info(f'm2m_changed_comment_mentioned_users, ,{action=}')
    
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
    instance.updated_at = timezone.now()
    if not instance.pk and instance.created_by:
        instance.updated_by = instance.created_by

    if not instance.due_date:
        board = instance.column.board
        instance.due_date = (board.created_at + timedelta(days=board.sprint_days)).date()


def generate_hash(data):
    json_data = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_data.encode('utf-8')).hexdigest()


def create_history(instance:Task, created:bool=False, changes:dict=None):
    # Build raw snapshot for hashing and diff
    logger.debug(f'{changes=}')
    raw_snapshot = model_to_dict(instance, exclude=['id', 'created_at', 'updated_at'])
    raw_snapshot['assigned_to'] = sorted(list(instance.assigned_to.values_list('id', flat=True)))
    raw_snapshot['tags'] = sorted(list(instance.tags.values_list('id', flat=True)))
    raw_snapshot = clean_for_json(raw_snapshot)
    
    if changes:
        raw_snapshot.update(changes)
    
    current_hash = generate_hash(raw_snapshot)
        

    latest_history = TaskHistory.objects.filter(task=instance).order_by('-id').first()

    # Create readable snapshot (for storage)
    readable_snapshot = model_to_dict(instance, exclude=['id', 'created_at', 'updated_at'])
    readable_snapshot['assigned_to'] = sorted(list(instance.assigned_to.values_list('name', flat=True)))
    readable_snapshot['tags'] = sorted(list(instance.tags.values_list('name', flat=True)))
    if instance.column:
        readable_snapshot['column'] = str(instance.column)
    if instance.created_by:
        readable_snapshot['created_by'] = str(instance.created_by)
    if instance.updated_by:
        readable_snapshot['updated_by'] = str(instance.updated_by)
    if instance.parent_task:
        readable_snapshot['parent_task'] = str(instance.parent_task)
    readable_snapshot = clean_for_json(readable_snapshot)

    if created or not latest_history:
        TaskHistory.objects.create(
            task=instance,
            updated_by=instance.updated_by,
            changes=readable_snapshot,
            snapshot=readable_snapshot,
            hash=current_hash
        )
        if created and instance.parent_task:
            instance.parent_task.total_sub_tasks += 1
            instance.parent_task.save(update_fields=['total_sub_tasks'])
        return

    if latest_history.hash == current_hash:
        logger.info("No changes detected for Task ID %s", instance.id)
        return

    # Only compare raw snapshots for diff
    previous_raw = clean_for_json(latest_history.snapshot)
    diff = {}

    for key in raw_snapshot:
        old_val = previous_raw.get(key)
        new_val = readable_snapshot.get(key)
        logger.debug(f'{key=}, from: {old_val}, to: {new_val}')

        # Sort lists for consistent comparison
        if isinstance(old_val, list):
            old_val = sorted(old_val or [])
        if isinstance(new_val, list):
            new_val = sorted(new_val or [])

        if old_val != new_val:
            diff[key] = {
                "from": previous_raw.get(key, old_val),
                "to": readable_snapshot.get(key, new_val)
            }

    if diff:
        TaskHistory.objects.create(
            task=instance,
            updated_by=instance.updated_by,
            changes=diff,
            snapshot=readable_snapshot,
            hash=current_hash
        )


@receiver(post_save, sender=Task)
def post_save_task(sender, instance: Task, created: bool, **kwargs):
    logger.info('post_save_task triggered for Task ID %s', instance.id)
    create_history(instance=instance, created=created)
    

@receiver(m2m_changed, sender=Task.tags.through)
def m2m_changed_task_tags(sender, instance:Task, action:str, pk_set:set[int], *args, **kwargs):
    logger.debug(f'm2m_changed_task_tags, {action=}')
    if action == 'post_add':
        changes = {}
        tags:set[int] = set(instance.tags.all().values_list('id',flat=True))
        new_tags = tags.union(pk_set)
        logger.debug(f'{new_tags=}')
        changes['tags'] = list(new_tags) if new_tags else list()
        create_history(instance=instance, changes=changes)
    elif action in ['post_remove','post_clear']:
        changes = {}
        tags = set(instance.tags.all().values_list('id',flat=True))
        new_tags = tags.difference_update(pk_set)
        logger.debug(f'{new_tags=}')
        changes['tags'] = list(new_tags) if new_tags else list()
        create_history(instance=instance, changes=changes)

@receiver(post_delete, sender=Task)
def post_delete_task(sender, instance:Task, *args, **kwargs):
    logger.debug('post_delete_task')
    if instance.parent_task:
        instance.parent_task.total_sub_tasks -= 1
        if instance.is_complete:
            instance.parent_task.completed_sub_tasks -= 1
        instance.parent_task.save(update_fields=['total_sub_tasks','completed_sub_tasks'])



@receiver(post_save, sender=Board)
def post_save_board(sender, instance:Board, created:bool, *args, **kwargs):
    logger.debug(f'post_save_board')
    if created:
        Column.objects.create(board=instance,name="Pending", created_by=instance.created_by, draft_column=True)

@receiver(pre_save, sender=Column)
def pre_save_column(sender, instance:Column, *args, **kwargs):
    logger.debug(f'pre_save_column')
    if not instance.pk and instance.board and not instance.board.columns.filter(draft_column=True).exists():
        instance.draft_column = True
