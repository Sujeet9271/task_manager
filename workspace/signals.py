from django.db.models.signals import post_save,pre_save,m2m_changed,post_delete
from django.dispatch import receiver
from notifications.models import Notification
from workspace.models import Workspace
from task_manager.logger import logger
from accounts.models import Users

@receiver(m2m_changed,sender = Workspace.members.through)
def create_board_member_notification(sender, instance: Workspace, action, reverse, model, pk_set, **kwargs):
    """Signal handler to create notifications when users are added or removed from a workspace."""
    logger.info(f'{action=}, {sender=}, {model=}, {instance=}, {pk_set=}')
    if instance.created_by_id in pk_set:
        return
    
    if action == 'post_add':  # Users are added
        message = f"Welcome! You've been added to the workspace: '{instance.name}'. Stay tuned for updates and tasks."
        Notification.create_notification(pk_set, 'assigned_to_workspace', instance, message)
    
    elif action in ['post_remove', 'post_clear']:  # Users are removed
        message = f"You've been removed from the workspace: '{instance.name}'. You will no longer receive updates for this workspace."
        Notification.create_notification(pk_set, 'removed_from_workspace', instance, message)