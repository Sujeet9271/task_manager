from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from accounts.models import Users

from task_manager.logger import logger

# Create your views here.


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
                return redirect('board:index')
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