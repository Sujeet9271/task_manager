from django import forms
from accounts.models import Users
from board.models import Board, Column, Task, SubTask


class TaskCreateForm(forms.ModelForm):

    class Meta:
        model = Task
        fields = ['title',]

class TaskForm(forms.ModelForm):
    assigned_to = forms.ModelMultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple(),queryset=Users.objects.all(),label='Assign Users')

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