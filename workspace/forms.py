from django import forms

from accounts.models import Users
from workspace.models import Workspace


class WorkSpaceForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(required=False,widget=forms.CheckboxSelectMultiple(),queryset=Users.objects.none(),label='Add Members')

    def __init__(self, user,*args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.auto_id='edit_%s'
        else:
            self.auto_id='id_%s'
        self.user = user
        if self.user: 
            self.fields['members'].queryset = Users.objects.all().exclude(id=self.user.id)
    
    def save(self, commit=True):
        """
        Save this form's self.instance object if commit=True. Otherwise, add
        a save_m2m() method to the form which can be called after the instance
        is saved manually at a later time. Return the model instance.
        """
        if self.errors:
            raise ValueError(
                "The %s could not be %s because the data didn't validate."
                % (
                    self.instance._meta.object_name,
                    "created" if self.instance._state.adding else "changed",
                )
            )
        if commit:
            # If committing, save the instance and the m2m data immediately.
            if self.instance and not self.instance.pk and self.user:
                self.instance.created_by = self.user
            self.instance.save()
            self._save_m2m()
        else:
            # If not committing, add a method to the form to allow deferred
            # saving of m2m data.
            self.save_m2m = self._save_m2m
        return self.instance

    class Meta:
        model = Workspace
        fields = ['name','members']