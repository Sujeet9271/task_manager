from django.db import models




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

    class Meta:
        abstract = True

class Board(SoftDeleteModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey('accounts.Users', on_delete=models.CASCADE, related_name='boards')
    members = models.ManyToManyField('accounts.Users', related_name='board_memberships', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


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


class Task(SoftDeleteModel):
    column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='tasks')
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

    def __str__(self):
        return self.title


class SubTask(SoftDeleteModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='subtasks')
    title = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title
