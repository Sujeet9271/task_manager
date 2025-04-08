from django import forms
from accounts.models import Users
from board.models import Attachment, Board, Column, Task
from workspace.models import Workspace

class TaskCreateForm(forms.ModelForm):

    class Meta:
        model = Task
        fields = ['title',]

class SubTaskCreateForm(forms.ModelForm):
    assigned_to = forms.ModelMultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple(),queryset=Users.objects.none(),label='Assign Users')

    def __init__(self, user:Users, task:Task, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task = task
        self.user = user
        self.fields['assigned_to'].queryset = task.assigned_to.all()

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

class TaskForm(forms.ModelForm):
    assigned_to = forms.ModelMultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple(),queryset=Users.objects.none(),label='Assign Users')

    def __init__(self, workspace:Workspace, user:Users, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.user = user
        if self.workspace:
            self.fields['assigned_to'].queryset = workspace.members.all()
        elif self.instance and self.instance.pk: 
            self.fields['assigned_to'].queryset = self.instance.column.board.members.all()

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
