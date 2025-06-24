from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

# Create your models here.

class Notification(models.Model):
    user = models.ForeignKey('accounts.Users', on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50,)
    
    # Generic Foreign Key to refer to any model (Task, Board, Comment, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.created_at}"

    def mark_as_read(self):
        self.read = True
        self.save()

    
    @classmethod
    def create_notification(cls, user, notification_type, content_object, message):
        content_type = ContentType.objects.get_for_model(content_object)
        if isinstance(user,(list,set, tuple)):
            bulk = []
            for id in user:
                notification = cls(
                    user_id=id,
                    notification_type=notification_type,
                    content_type=content_type,
                    object_id=content_object.id,
                    content_object=content_object,
                    message=message
                )
                bulk.append(notification)
            cls.objects.bulk_create(bulk, batch_size=1000)
        else:
            return cls.objects.create(
            user_id=user,
            notification_type=notification_type,
            content_type=content_type,
            object_id=content_object.id,
            content_object=content_object,
            message=message
        )

    class Meta:
        ordering = ['-updated_at']
