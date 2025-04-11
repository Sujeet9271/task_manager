from datetime import datetime
from django.db import models
from accounts.models import Users
# Create your models here.

class Workspace(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True,related_name='workspace')
    members = models.ManyToManyField(Users, related_name='workspaces')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True,blank=True)

    def __str__(self):
        return f'{self.name}'
    

    def delete(self):
        self.is_deleted=True
        self.deleted_at = datetime.now()
        self.save(update_fields=['is_deleted','updated_at','deleted_at'])
    
