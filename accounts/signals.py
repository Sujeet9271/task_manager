from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import smart_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMessage
from django.contrib.sites.models import Site

from django.conf import settings

from django.template.loader import render_to_string
from django.urls import reverse
from accounts.models import Users
from task_manager.logger import logger

from decouple import config
import threading

class EmailThread(threading.Thread):
    def __init__(self,email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        self.email.send()


@receiver(post_save,sender=Users)
def pre_save_user(sender, instance:Users, *args, **kwargs):
    logger.info('pre_save_user')
    try:
        if not instance.pk and not instance.is_superuser:
            instance.is_active = False
    except Exception as e:
        logger.exception(stack_info=False, msg=f"Exception={e.args}")
        raise e

@receiver(post_save,sender=Users)
def post_save_user(sender, instance:Users, created:bool, *args, **kwargs):
    logger.info('post_save_user')
    try:
        if created and not instance.is_superuser:
            uidb64 = urlsafe_base64_encode(smart_bytes(instance.id))
            token = PasswordResetTokenGenerator().make_token(instance)
            relativeLink = reverse('accounts:password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
            baseurl = Site.objects.get_current().domain
            absurl = f"{baseurl}{relativeLink}"
            email_body = render_to_string('accounts/auth/password/password_reset_email_body.html', {'reset_url': absurl,'uidb64':uidb64,'token':token,'domain':baseurl,'user':instance,'reply_mail':settings.EMAIL_HOST_USER})
            email = EmailMessage(subject='Account Activation: Establish Your Secure Password' ,body=email_body, from_email=settings.EMAIL_HOST_USER, to=[instance.email])
            email.content_subtype = 'html'
            EmailThread(email).start()
    except Exception as e:
        logger.exception(stack_info=False, msg=f"Exception={e.args}")
        raise e