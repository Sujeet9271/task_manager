import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from typing import Any
from accounts.models import Users
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, PasswordChangeForm as PCF, SetPasswordForm as SPF, _unicode_ci_compare
from django.template import loader
from django.core.mail import EmailMessage

from accounts.signals import EmailThread

def is_valid_mail(email):
    pattern = r'^[\w\.-]+@[a-zA-Z\d\.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))



class UserSignupForm(UserCreationForm):
    email = forms.EmailField(label='Email',required=True)
    username = forms.CharField(label='Username', min_length=3, max_length=150,required=True,widget=forms.TextInput())
    name = forms.CharField(label='Name', min_length=3, max_length=150,required=True,widget=forms.TextInput())
    password1=None
    password2=None


    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
  
    def clean_email(self):  
        email = self.cleaned_data['email'].lower()
        if not is_valid_mail(email):
            self.add_error('email','Please enter valid email address')
        new = Users.objects.filter(email=email)  
        if new.exists():  
            self.add_error('email','Account with Email already exists')
        return email 

    
    def save(self,commit=True):
        username = self.cleaned_data.get('email').split('@')[0]
        user = Users.objects.create_user( 
            email=self.cleaned_data['email'],  
            username=username,
            name=self.cleaned_data['name'], 
        )  
        return user 

    class Meta:
        model=Users
        fields = ['email','username','name',]



class CustomPasswordResetForm(PasswordResetForm):


    def get_users(self, email):
        """Given an email, return matching user(s) who should receive a reset.

        This allows subclasses to more easily customize the default policies
        that prevent inactive users and users with unusable passwords from
        resetting their password.
        """
        email_field_name = Users.get_email_field_name()
        active_users = Users._default_manager.filter(**{
            '%s__iexact' % email_field_name: email,
        })
        return (
            u for u in active_users
            if u.has_usable_password() and
            _unicode_ci_compare(email, getattr(u, email_field_name))
        )

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)
        email = EmailMessage(subject=subject,body=body, from_email=from_email,to=[to_email])
        email.content_subtype = 'html'
        EmailThread(email).start()




class CustomSetPasswordForm(SPF):
   
    def clean_new_password2(self):
        super().clean()
        password = self.cleaned_data["new_password1"]
        if self.user.check_password(password):
            self.add_error('new_password1','New Password cannot be Old Password')
        return password

    def save(self, commit=True):       
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.is_active=True
            self.user._changed_password=True
            self.user.save()
        return self.user