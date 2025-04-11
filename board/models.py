from datetime import datetime
from django.db import models
from django.db.models import FileField
from django.forms import ValidationError
from django.template.defaultfilters import filesizeformat
from django.urls import reverse

from task_manager.utils import get_full_url


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def deleted(self):
        return super().get_queryset().filter(is_deleted=True)

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(auto_now=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # For accessing all objects, including deleted ones

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.deleted_at = datetime.now()
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('accounts.Users', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name
    

    def get_full_url(self, request):
        """Generate the full URL for the board view."""
        return get_full_url('board:board-view', args=[self.id])


class Column(SoftDeleteModel):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)  # for drag-and-drop
    created_by = models.ForeignKey('accounts.Users', on_delete=models.SET_NULL, null=True, related_name='board_columns')
    updated_by = models.ForeignKey('accounts.Users', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.board.name})"
    

    def get_tasks(self, user):
        return self.tasks.filter(assigned_to=user, parent_task__isnull=True) if not user.is_staff else self.tasks.filter(parent_task__isnull=True)
    
    class Meta:
        ordering = ['board','order']  # Order by the 'order' field



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
    

class Task(SoftDeleteModel):
    column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='tasks')
    parent_task = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_to = models.ManyToManyField('accounts.Users', related_name='assigned_tasks', blank=True)
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=20, choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], default='Medium')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.Users', on_delete=models.SET_NULL, null=True, related_name='tasks')
    updated_by = models.ForeignKey('accounts.Users', on_delete=models.SET_NULL, null=True)
    extra_data = models.JSONField(default=dict, null=True, blank=True)
    is_complete = models.BooleanField(default=False)

    def __str__(self):
        if self.parent_task:
            return f'SubTask: {self.title}'
        return f'Task: {self.title}'
    

class TaskHistory(SoftDeleteModel):
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='history')
    updated_by = models.ForeignKey('accounts.Users', on_delete=models.SET_NULL, null=True, blank=True)
    changes = models.JSONField(default=dict)
    snapshot = models.JSONField(default=dict)  # ← full cleaned snapshot
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hash = models.TextField(blank=True)

    def __str__(self):
        return f'History: {self.task_id}, Changes by: {self.updated_by_id}'

    


class Attachment(models.Model):
    workspace = models.ForeignKey('workspace.Workspace',on_delete=models.SET_NULL,null=True,blank=True, related_name='workspace_attachment')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = ContentTypeRestrictedFileField(
        upload_to=location,
        content_types=['application/pdf', 'application/zip', 'image/jpeg', 'image/png', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/plain', 'text/csv', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'],
        max_upload_size=10485760
    )
    type = models.CharField(max_length=10, choices=[('file','File'),('url','URL')],default='file')
    name = models.CharField(max_length=255, null=True, blank=True)
    url = models.URLField(null=True,blank=True)
    uploaded_by = models.ForeignKey("accounts.Users",on_delete=models.SET_NULL,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    

class Comments(models.Model):
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="comments")
    comment = models.TextField()
    added_by = models.ForeignKey("accounts.Users", on_delete=models.SET_NULL, null=True, blank=True, related_name="comments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    mentioned_users = models.ManyToManyField("accounts.Users", related_name='mentioned_in_comments', blank=True)

    def __str__(self):
        return self.comment
