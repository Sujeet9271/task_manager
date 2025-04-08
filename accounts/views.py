from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from accounts.models import Users
from accounts.forms import CustomPasswordResetForm, CustomSetPasswordForm, UserSignupForm
from workspace.models import Workspace
from django.contrib.auth.views import PasswordResetView,PasswordResetConfirmView, PasswordResetCompleteView, PasswordResetDoneView

from task_manager.logger import logger

# Create your views here.

def register_user(request):
    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('accounts:account_created_msg')  # Replace with your desired page
    else:
        form = UserSignupForm()
    return render(request, 'accounts/signup.html', {'form': form})


def account_created_msg(request):
    if not request.META.get('HTTP_REFERER'):
        return redirect('accounts:login-user')
    return render(request,'accounts/auth/account_created_msg.html')


def email_login(request):
    context= {}
    try:
        if request.user and request.user.is_authenticated:
            return redirect('board:index')
        
        next = request.GET.get('next')
        if request.method=='POST':
            username=request.POST['username']
            password=request.POST['password']
            user:Users = authenticate(request=request,username=username,password=password)
            if user:
                login(request,user)
                if next:
                    return redirect(next)
                return redirect('workspace:index')
    except Exception as e:
        messages.error(request,e.args[0])
        logger.exception(stack_info=False, msg=f"Exception={e.args}")
    return render(request,'accounts/login.html',context)


@require_POST
@login_required
def logout_user(request):
    try:
        logout(request)
        return redirect('board:index')
    except Exception as e:
        messages.error(request, e.args[0])
        logger.exception(stack_info=False, msg=f"Exception={e.args}")
    return render(request, 'accounts/login.html')



class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/auth/password/password_reset.html'

    # html_email_template_name="accounts/password_reset_email.html"
    # email_template_name = "accounts/password_reset_email.html"

    html_email_template_name="accounts/auth/password/password_reset_email.html"
    email_template_name = "accounts/auth/password/password_reset_email.html"

    subject_template_name = "accounts/password_reset_subject.txt"
    extra_email_context = {'reply_mail':settings.EMAIL_HOST_USER}

    form_class = CustomPasswordResetForm
    success_url = reverse_lazy("accounts:password_reset_done")
    

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/auth/password/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")
    form_class = CustomSetPasswordForm
    post_reset_login=False # True, will automatically login the user after password reset


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/auth/password/password_reset_complete.html'
    title = 'Password Reset Complete'

    def get(self, request, *args, **kwargs) -> HttpResponse:
        if not request.META.get('HTTP_REFERER'):
            return redirect('accounts:login-user')
        return super().get(request, *args, **kwargs)
    
class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name='accounts/auth/password/password_reset_done.html'

