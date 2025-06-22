from datetime import date
from django import forms
from accounts.models import Users
from board.models import Attachment, Board, Column, Comments, Task
from workspace.models import Workspace
from task_manager.logger import logger



class TaskCreateForm(forms.ModelForm):

    class Meta:
        model = Task
        fields = ['title',]

class SubTaskCreateForm(forms.ModelForm):
    # assigned_to = forms.ModelMultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple(),queryset=Users.objects.none(),label='Assign Users')

    def __init__(self, user:Users, task:Task, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.auto_id='edit_%s'
        else:
            self.auto_id='id_%s'
        self.task = task
        self.user = user
        # self.fields['assigned_to'].queryset = task.assigned_to.all()

    def clean(self):
        super().clean()
        if self.instance and self.instance.pk:
            if not self.user.is_staff and not self.instance.assigned_to.filter(id=self.user.id).exists():
                self.add_error(None,"You have no permission to edit this task")
        return self.cleaned_data

    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'priority', 'assigned_to']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4, 'cols': 40}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'title': 'Task Title',
            'description': 'Task Description',
            'due_date': 'Due Date',
            'priority': 'Priority',
        }


class BoardForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple(),queryset=Users.objects.none(),label='Assign Users')

    def __init__(self, workspace:Workspace, user:Users, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.auto_id='edit_%s'
        else:
            self.auto_id='id_%s'
        self.workspace = workspace
        self.user = user
        
        self.fields['members'].queryset = workspace.members.all().exclude(id=user.id)
        
    class Meta:
        model = Board
        fields = ['name','sprint_days','members']
    



class TaskForm(forms.ModelForm):
    assigned_to = forms.ModelMultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple(),queryset=Users.objects.none(),label='Assign Users')

    def __init__(self, workspace:Workspace, user:Users, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.auto_id='edit_%s'
        else:
            self.auto_id='id_%s'
        self.workspace = workspace
        self.user = user
        
        if self.instance and self.instance.pk: 
            exclude_users = [self.instance.created_by_id, user.id]
            if self.instance.parent_task:
                exclude_users.append(self.instance.parent_task.created_by_id)
                self.fields['assigned_to'].queryset = self.instance.parent_task.assigned_to.all().exclude(id__in=exclude_users)
            else:
                self.fields['assigned_to'].queryset = self.instance.column.board.members.all().exclude(id__in=exclude_users)
        elif self.workspace:
            self.fields['assigned_to'].queryset = workspace.members.all().exclude(id=user.id)
        
        self.fields['due_date'].widget.attrs.update({'min':f"{str(date.today())}"})
        if self.instance and self.instance.parent_task and self.instance.parent_task.due_date:
            self.fields['due_date'].widget.attrs.update({'max':f"{str(self.instance.parent_task.due_date)}"})
            if self.instance.parent_task.due_date == date.today():
                self.fields['due_date'].widget.attrs.update({'value':f"{str(self.instance.parent_task.due_date)}"})

        

    def clean(self):
        super().clean()
        if self.instance and self.instance.pk:
            if not self.user.is_staff and not self.instance.assigned_to.filter(id=self.user.id).exists():
                self.add_error(None,"You have no permission to edit this task")
        return self.cleaned_data

    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'priority', 'assigned_to']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4, 'cols': 40}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'title': 'Task Title',
            'description': 'Task Description',
            'due_date': 'Due Date',
            'priority': 'Priority',
        }



class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ['file', 'type', 'url', 'name']
        widgets = {
            'file': forms.ClearableFileInput(),  # don't set multiple=True here
            'url': forms.URLInput(attrs={'placeholder': 'https://example.com'}),
            'name': forms.TextInput(attrs={'placeholder': 'Optional name for the URL'}),
        }


class CommentForm(forms.ModelForm):

    class Meta:
        model = Comments
        fields = ['comment']