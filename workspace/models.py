from datetime import datetime
from django.db import models
from accounts.models import Users
# Create your models here.

from django.db import models
from django.utils import timezone

class Workspace(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        'accounts.Users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workspaces_created',
        db_index=True  # likely filtered by created_by
    )
    members = models.ManyToManyField(
        'accounts.Users',
        related_name='workspaces'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False, db_index=True)  # often filtered
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
        return self

    class Meta:
        indexes = [
            models.Index(fields=['is_deleted']),
            models.Index(fields=['created_by']),
        ]

