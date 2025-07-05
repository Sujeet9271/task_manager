from datetime import datetime
import site
from uuid import uuid4
from django.db import models
from django.db.models import FileField, Manager, Case, When, Value, IntegerField
from django.forms import ValidationError
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils import timezone
from django.contrib.sites.models import Site
from django.urls import reverse

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def deleted(self):
        return super().get_queryset().filter(is_deleted=True)

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(default=timezone.now)

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # For accessing all objects, including deleted ones

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
        return self

    class Meta:
        abstract = True

class Board(SoftDeleteModel):
    workspace = models.ForeignKey('workspace.Workspace', on_delete=models.SET_NULL, null=True, blank=True, related_name='boards')
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey('accounts.Users', on_delete=models.CASCADE, related_name='boards')
    members = models.ManyToManyField('accounts.Users', related_name='board_memberships', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    updated_by = models.ForeignKey('accounts.Users', on_delete=models.SET_NULL, null=True)
    sprint_days = models.PositiveIntegerField(default=7)
    private = models.BooleanField(default=False)
    uuid       = models.UUIDField(default=uuid4, unique=True,)

    def __str__(self):
        return self.name
    

    def get_full_url(self, request):
        """Generate the full URL for the board view."""
        relative_url = reverse('board:board-view', args=[self.id])
        return request.build_absolute_uri(relative_url)
    

    def get_invite_link(self):
        relativeLink = reverse('board:board-invite', kwargs={'board_uuid': self.uuid})
        baseurl = Site.objects.get_current().domain
        invite_link = f"{baseurl}{relativeLink}"
        return invite_link
    
    class Meta:
        verbose_name = 'Board'
        verbose_name_plural = 'Boards'
        indexes = [
            models.Index(fields=['is_deleted']),
            models.Index(fields=['workspace']),
            models.Index(fields=['created_by']),
        ]



class Column(SoftDeleteModel):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)  # for drag-and-drop
    created_by = models.ForeignKey('accounts.Users', on_delete=models.SET_NULL, null=True, related_name='board_columns')
    updated_by = models.ForeignKey('accounts.Users', on_delete=models.SET_NULL, null=True)
    draft_column = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.board.name})"
    

    def get_tasks(self, user):
        return self.tasks.filter(assigned_to=user, parent_task__isnull=True) if not user.is_staff else self.tasks.filter(parent_task__isnull=True)
    
    class Meta:
        ordering = ['board','-draft_column','order']  # Order by the 'order' field
        verbose_name = 'Column'
        verbose_name_plural = 'Columns'
        indexes = [
            models.Index(fields=['is_deleted']),
            models.Index(fields=['created_by']),
        ]



def location(instance,filename):
    return f'attachments/workspace_{instance.workspace_id}/task_{instance.task_id}/{filename}'



class ContentTypeRestrictedFileField(FileField):
    """
    Same as FileField, but with additional constraints:
        * content_types - List of allowed content types (e.g., ['application/pdf', 'image/jpeg'])
        * max_upload_size - Maximum file size allowed for upload in bytes.
            - 2.5MB  = 2621440
            - 5MB    = 5242880
            - 10MB   = 10485760
            - 20MB   = 20971520
            - 50MB   = 52428800
            - 100MB  = 104857600
            - 250MB  = 214958080
            - 500MB  = 429916160
    """

    def __init__(self, *args, **kwargs):
        self.content_types = kwargs.pop("content_types", [])
        self.max_upload_size = kwargs.pop("max_upload_size", None)
        super().__init__(*args, **kwargs)


    def clean(self, data, *args, **kwargs):
        data = super().clean(data, *args, **kwargs)
        if not data:
            return data

        file = getattr(data, 'file', None)
        errors = []

        # Check content type
        content_type = getattr(file, "content_type", None)
        if self.content_types and content_type not in self.content_types:
            errors.append("File type not supported.")

        # Check file size
        if self.max_upload_size and file.size > self.max_upload_size:
            errors.append(
                f"File too large ({filesizeformat(file.size)}). Maximum size: {filesizeformat(self.max_upload_size)}"
            )

        if errors:
            raise ValidationError(errors)  # Correctly passing as a list

        return data
    

class TaskManager(SoftDeleteManager):

    def order_by_priority(self):
        return super().get_queryset().annotate(
            priority_order=Case(
                When(priority='High', then=Value(1)),
                When(priority='Medium', then=Value(2)),
                When(priority='Low', then=Value(3)),
                default=Value(4),
                output_field=IntegerField()
            )
        ).order_by('priority_order', 'order', '-created_at')


class Tag(SoftDeleteModel):
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#FFFFFF')  # HEX code
    created_by = models.ForeignKey('accounts.Users', on_delete=models.SET_NULL, null=True, related_name='tags')

    def __str__(self):
        return f'#{self.name}'
    
    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Labels'
        indexes = [
            models.Index(fields=['is_deleted']),
            models.Index(fields=['created_by']),
        ]


class Task(SoftDeleteModel):
    column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='tasks', db_index=True)
    parent_task = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sub_tasks'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_to = models.ManyToManyField('accounts.Users', related_name='assigned_tasks', blank=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    priority = models.CharField(
        max_length=20,
        choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')],
        default='Medium',
        db_index=True
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey('accounts.Users', on_delete=models.SET_NULL, null=True, related_name='tasks')
    updated_by = models.ForeignKey('accounts.Users', on_delete=models.SET_NULL, null=True, blank=True)
    extra_data = models.JSONField(default=dict, null=True, blank=True)
    is_complete = models.BooleanField(default=False, db_index=True)
    tags = models.ManyToManyField(Tag, related_name='tasks', blank=True)

    total_sub_tasks = models.PositiveIntegerField(default=0)
    completed_sub_tasks = models.PositiveIntegerField(default=0)

    objects = TaskManager()

    def __str__(self):
        return f'SubTask: {self.title}' if self.parent_task else f'Task: {self.title}'

    def clean(self):
        from django.core.exceptions import ValidationError

        # If this task is set as a subtask (i.e., has a parent_task)
        # Then it should not itself be a parent to any other task
        if self.pk and self.parent_task and Task.objects.filter(parent_task=self).exists():
            raise ValidationError("Subtasks cannot have their own subtasks.")

        # If parent_task is itself a subtask, prevent nesting
        if self.parent_task and self.parent_task.parent_task is not None:
            raise ValidationError("Cannot assign a subtask as parent. Nested subtasks are not allowed.")
        
        if self.pk and not self.updated_by:
            raise ValidationError({'updated_by','Updating user not specified'})
        
    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
        
        if self.parent_task:
            self.parent_task.total_sub_tasks -= 1
            if self.is_complete:
                self.parent_task.completed_sub_tasks -= 1
            self.parent_task.save(update_fields=['total_sub_tasks','completed_sub_tasks'])
        return self

    def save(self, *args, **kwargs):
        self.full_clean()  # Enforces clean() during save
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        ordering = ['column','-updated_at']
        indexes = [
            models.Index(fields=['is_deleted']),
            models.Index(fields=['column', 'order']),
            models.Index(fields=['created_by']),
            models.Index(fields=['priority']),
            models.Index(fields=['is_complete']),
        ] 



class Attachment(models.Model):
    workspace = models.ForeignKey('workspace.Workspace',on_delete=models.SET_NULL,null=True,blank=True, related_name='workspace_attachment')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = ContentTypeRestrictedFileField(
        upload_to=location,
        content_types=['application/pdf', 'application/zip', 'image/jpeg', 'image/png', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/plain', 'text/csv', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'],
        max_upload_size=10485760
    )
    type = models.CharField(max_length=10, choices=[('file','File'),('url','URL')],default='file')
    file_type = models.CharField(max_length=100, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    url = models.URLField(null=True,blank=True)
    uploaded_by = models.ForeignKey("accounts.Users",on_delete=models.SET_NULL,null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def attachment_url(self):
        if self.type=='file' and self.file:
            return self.file.url
        elif self.type=='url' and self.url:
            return self.url
        return None

    def attachment_name(self):
        if self.type=='file' and self.file:
            return self.file.name
        elif self.type=='url' and self.url:
            return self.name if self.name else self.url
        return None
    
    def __str__(self):
        """Returns a readable string representation of the attachment."""
        if self.task and self.file and self.file.name:
            return f"Attachment ({self.file.name}) for Task ID {self.task_id}"
        return "Attachment"
    
    def file_size(self):
        """Returns the file size in KB or MB."""
        if self.file:
            size_kb = self.file.size / 1024
            return f"{size_kb:.2f} KB" if size_kb < 1024 else f"{size_kb / 1024:.2f} MB"
        return "Unknown Size" if self.type == 'file' else None
    
    class Meta:
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments'
        indexes = [
            models.Index(fields=['workspace']),
            models.Index(fields=['task']),
            models.Index(fields=['uploaded_by']),
        ]


class Comments(models.Model):
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="comments")
    comment = models.TextField()
    added_by = models.ForeignKey("accounts.Users", on_delete=models.SET_NULL, null=True, blank=True, related_name="comments")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    mentioned_users = models.ManyToManyField("accounts.Users", related_name='mentioned_in_comments', blank=True)

    def __str__(self):
        return self.comment

    class Meta:
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments' 
        indexes = [
            models.Index(fields=['task']),
            models.Index(fields=['added_by']),
            models.Index(fields=['created_at']),
        ]



class TaskHistory(SoftDeleteModel):
    task = models.ForeignKey(
        'Task',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='history',
    )
    updated_by = models.ForeignKey(
        'accounts.Users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    changes = models.JSONField(default=dict, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)
    hash = models.CharField(max_length=128, blank=True, db_index=True)  # assume hash is SHA-like
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'History for Task #{self.task_id} by User #{self.updated_by_id}'
    
    class Meta:
        verbose_name = 'Task History'
        verbose_name_plural = 'Task Histories'
        ordering = ['-created_at']  # show recent changes first
        indexes = [
            models.Index(fields=['is_deleted']),
            models.Index(fields=['task']),
            models.Index(fields=['updated_by']),
            models.Index(fields=['hash']),
            models.Index(fields=['-created_at']),
        ]



class BoardFilter(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='filters')
    user = models.ForeignKey('accounts.Users', on_delete=models.CASCADE, related_name='filters')
    filter = models.JSONField(default=dict)
    board_view = models.CharField(max_length=5, choices=[('card','Card'),('table','Table')], default='card')

    class Meta:
        db_table = 'board_filter'
        verbose_name = 'Board Filter'
        verbose_name_plural = 'Board Filters'