from django.db.models.signals import post_save,pre_save,m2m_changed,post_delete
from django.dispatch import receiver
from workspace.models import Workspace
from task_manager.logger import logger
from accounts.models import Users

@receiver(m2m_changed,sender = Workspace.members.through)
def m2m_changed_workspace_members(sender,*args, **kwargs):
    logger.info(msg='m2m_changed_workspace_members')
    instance:Workspace = kwargs.get('instance')
    action:str = kwargs.get('action')
    try:
        if action.startswith('pre'):
            return 
        
        if action in ['post_remove','post_clear']:
            users = kwargs.get('pk_set')
        elif action == 'post_add':
            users = kwargs.get('pk_set')
        else:
            return

    except Exception as e:
        logger.exception(msg=e.args,stack_info=False)