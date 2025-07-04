from datetime import date, timedelta
from django import forms
from accounts.models import Users
from board.models import Attachment, Board, Column, Comments, Tag, Task
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


class BoardCreateForm(forms.ModelForm):

    def __init__(self, user:Users, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.auto_id='edit_%s'
        else:
            self.auto_id='id_%s'
        self.user = user
                
    class Meta:
        model = Board
        fields = ['name','sprint_days','private']

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
        self.fields['members'].label_from_instance = lambda obj: f"{obj.name}" if obj.name else f"{obj.username}"
        self.fields['members'].queryset = workspace.members.all().exclude(id=user.id)
        
    class Meta:
        model = Board
        fields = ['name','sprint_days','members','private']
    



class TaskForm(forms.ModelForm):
    assigned_to = forms.ModelMultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple(),queryset=Users.objects.none(),label='Assign Users')
    tags = forms.ModelMultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple(),queryset=Tag.objects.all(),label='Tags')

    def __init__(self, workspace:Workspace, user:Users, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.auto_id='edit_%s'
        else:
            self.auto_id='id_%s'
        self.workspace = workspace
        self.user = user

        self.fields['assigned_to'].label_from_instance = lambda obj: f"{obj.name}" if obj.name else f"{obj.username}"

        self.fields['due_date'].widget.attrs.update({'min':f"{str(date.today())}"})
        self.fields['due_date'].widget.attrs.update({'value':f"{str(date.today())}"})
        instance: Task = self.instance
        if instance and instance.pk: 
            self.fields['due_date'].widget.attrs.update({'min':f"{str(instance.created_at.date())}"})
            exclude_users = [instance.created_by_id, user.id]
            if instance.parent_task:
                exclude_users.append(instance.parent_task.created_by_id)
                if instance.created_by == user:
                    self.fields['assigned_to'].queryset = instance.parent_task.assigned_to.all().exclude(id__in=exclude_users)
                else:
                    self.fields['assigned_to'].queryset = instance.assigned_to.all()
                    self.fields['assigned_to'].widget.attrs['readonly'] = True
                    self.fields['assigned_to'].disabled = True
                if instance.parent_task.due_date:
                    self.fields['due_date'].widget.attrs.update({'max':f"{str(instance.parent_task.due_date)}"})
                    if instance.parent_task.due_date == date.today():
                        self.fields['due_date'].widget.attrs.update({'value':f"{str(instance.parent_task.due_date)}"})
            else:
                if instance.created_by == user:
                    self.fields['assigned_to'].queryset = instance.column.board.members.all().exclude(id__in=exclude_users)
                else:
                    self.fields['assigned_to'].queryset = instance.assigned_to.all()
                    self.fields['assigned_to'].widget.attrs['readonly'] = True
                    self.fields['assigned_to'].disabled = True

                board = instance.column.board
                sprint_end = (board.created_at + timedelta(days=board.sprint_days)).date()
                logger.debug(f'{sprint_end=}')
                
                self.fields['due_date'].widget.attrs.update({
                                                            "value":f"{str(sprint_end)}",
                                                            "max":f"{str(sprint_end)}"
                                                        })
        elif self.workspace:
            self.fields['assigned_to'].queryset = workspace.members.all().exclude(id=user.id)

    def clean(self):
        super().clean()
        if self.instance and self.instance.pk:
            if not self.user.is_staff and not self.instance.assigned_to.filter(id=self.user.id).exists():
                self.add_error(None,"You have no permission to edit this task")
        return self.cleaned_data

    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'priority', 'assigned_to','tags']
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


class TaskFilterForm(forms.Form):
    search = forms.CharField(required=False, label="Search", widget=forms.TextInput(attrs={'placeholder': 'Search title or description'}))
    due_after = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    due_before = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    assigned_to = forms.ModelMultipleChoiceField(
        queryset=Users.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    priority = forms.ChoiceField(
        choices=[('', 'Select Priority'), ('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')],
        required=False
    )

    is_complete = forms.ChoiceField(
        choices=[('', 'Select Task Status'), ('all', 'All'), ('true', 'Completed'), ('false', 'Incomplete')],
        required=False
    )


    def __init__(self, board:Board, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.debug(f'{args=}')
        logger.debug(f'{kwargs=}')
        self.board = board
        self.auto_id = 'filter_%s'

        self.fields['assigned_to'].queryset = board.members.all()
        self.fields['assigned_to'].label_from_instance = lambda obj: f"{obj.name}" if obj.name else f"{obj.username}"

        self.fields['due_after'].widget.attrs.update({'min':f"{str(board.created_at.date())}"})
        sprint_end = (board.created_at + timedelta(days=board.sprint_days)).date()                
        self.fields['due_before'].widget.attrs.update({
                                                    "min":f"{str(board.created_at.date())}",
                                                    "max":f"{str(sprint_end)}"
                                                })

    class Meta:
        model = Task
        fields = ['search','due_after','due_before','assigned_to','tags','priority','is_complete']



class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = '__all__'
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
        }
