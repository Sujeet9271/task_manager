import json
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.db.models import QuerySet
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Page
from board.forms import BoardForm
from board.models import Board
from notifications.views import get_notifications
from workspace.forms import WorkSpaceForm
from workspace.models import Workspace
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh
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
    try:
        workspace = Workspace.objects.get(id=workspace_id)
        boards:QuerySet[Board] = request.user.board_memberships.filter(workspace=workspace).exclude(is_deleted=True)
        context['boards'] = boards
        context['workspace_id'] = workspace_id
        context['users'] = workspace.members.all()
        context['unread_notification_count'] = request.user.notifications.filter(read=False).count()
        context:dict = get_notifications(user=request.user, page_number=1, context=context)
        return render(request,'boards/index.html',context)
    except Workspace.DoesNotExist:
        return redirect('workspace:index')


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



@require_http_methods(['GET','POST','DELETE'])
@login_required
def board_actions(request,workspace_id,board_id):
    try:
        board:Board = Board.objects.get(workspace_id=workspace_id,id=board_id, created_by=request.user)
        if request.method=='DELETE':
            board.delete()
            return HttpResponse(status=200)
        form = BoardForm(workspace=board.workspace,user=request.user, instance=board, data=request.POST or None)
        if request.method == 'POST' and form.is_valid():
            instance:Board = form.save()
            instance.members.add(request.user)
            response = render(request,'boards/components/board_list_item.html',{'board':instance})
            triggers = {}
            triggers["closeModal"] = {"modal_id": "close_editBoardModal", "level": "info"}
            response['HX-Trigger'] = json.dumps(triggers)
            return response
        return render(request,'boards/components/board_edit.html',{'form':form})
    except Exception as e:
        logger.exception(stack_info=False, msg=str(e))
        if request.htmx:
            redirect_url = reverse('workspace:index')
            return HttpResponseClientRedirect(redirect_to=redirect_url)
        return redirect('workspace:index')
