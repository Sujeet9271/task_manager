from django.db import models
from accounts.models import Users
# Create your models here.

class Workspace(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True,related_name='workspace')
    members = models.ManyToManyField(Users, related_name='workspaces')

    def __str__(self):
        return f'{self.name}'
    
