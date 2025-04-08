from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.db.models import QuerySet
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from board.models import Board
from workspace.forms import WorkSpaceForm
from workspace.models import Workspace
from django_htmx.http import HttpResponseClientRedirect
from task_manager.logger import logger
# Create your views here.



@require_http_methods(['GET',])
@login_required
def index(request):
    workspaces = Workspace.objects.filter(members=request.user)
    return render(request, 'workspace/index.html',{"workspaces":workspaces,"form":WorkSpaceForm(user=request.user)})


@require_http_methods(['POST'])
@login_required
def workspace_create(request):
    form = WorkSpaceForm(user=request.user, data=request.POST)
    if form.is_valid():
        instance:Workspace = form.save(commit=False)
        instance.created_by = request.user
        instance.save()
        form.save_m2m()
        instance.members.add(instance.created_by)
        redirect_url = reverse('workspace:get_workspace_boards',kwargs={'workspace_id':instance.id})
        return HttpResponseClientRedirect(redirect_to=redirect_url)
    return render(request,"workspace/components/create.html",{'form':form})


@require_http_methods(['GET'])
@login_required
def get_workspace_boards(request,workspace_id):
    context = {}
    workspace = Workspace.objects.get(id=workspace_id)
    boards:QuerySet[Board] = request.user.board_memberships.filter(workspace=workspace)
    context['boards'] = boards
    context['workspace_id'] = workspace_id
    return render(request,'boards/index.html',context)


@require_http_methods(['GET','POST','DELETE'])
@login_required
def workspace_actions(request,workspace_id):
    try:
        workspace = Workspace.objects.get(id=workspace_id)
        if request.method=='DELETE':
            workspace.delete()
            return HttpResponse(status=200)
            redirect_url = reverse('workspace:index')
            return HttpResponseClientRedirect(redirect_to=redirect_url)
        form = WorkSpaceForm(user=request.user,instance=workspace, data=request.POST or None)
        if request.method == 'POST' and form.is_valid():
            instance = form.save()
            response = render(request, "workspace/components/workspace_card.html", {"workspace": instance})
            response['HX-Trigger'] = 'workspaceEdited'
            return response
        return render(request,'workspace/components/edit.html',{'form':form})
    except Exception as e:
        logger.exception(stack_info=False, msg=str(e))
        if request.htmx:
            redirect_url = reverse('workspace:index')
            return HttpResponseClientRedirect(redirect_to=redirect_url)
        return redirect('workspace:index')
