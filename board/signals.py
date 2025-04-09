from django.db.models.signals import post_save, pre_save, m2m_changed, post_delete
from django.dispatch import receiver
from board.models import Board, Column, Task, Comments
from notifications.models import Notification
from task_manager.logger import logger
from accounts.models import Users

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
