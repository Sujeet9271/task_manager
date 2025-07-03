import json
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.db.models import QuerySet
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Page
from board.forms import BoardCreateForm, BoardForm, TaskFilterForm
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
    context = {}
    workspaces = Workspace.objects.filter(members=request.user).exclude(is_deleted=True)
    context["workspaces"] = workspaces
    context["form"] =  WorkSpaceForm(user=request.user)
    context['view_name'] = 'Workspace'
    return render(request, 'workspace/index.html',context)


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
        workspace = Workspace.objects.get(id=workspace_id, members=request.user)
        boards:QuerySet[Board] = Board.objects.prefetch_related('columns').filter(workspace=workspace, members=request.user).exclude(is_deleted=True)
        context['boards'] = boards
        context['workspace_id'] = workspace_id
        context['users'] = workspace.members.all()
        context['view_name'] = 'Board'
        context['board_create_form'] = BoardCreateForm(user=request.user)
        context:dict = get_notifications(user=request.user, page_number=1, context=context)
        return render(request,'boards/index.html',context)
    except Workspace.DoesNotExist:
        return redirect('workspace:index')


@require_http_methods(['GET','POST','DELETE'])
@login_required
def workspace_actions(request,workspace_id):
    try:
        workspace = Workspace.objects.get(id=workspace_id, created_by=request.user)
        if request.method=='DELETE':
            workspace.delete()
            response = HttpResponse(status=200)
            triggers = {}
            triggers["showToast"] = {"message":"Workspace Deleted", "level":"danger"}
            response['HX-Trigger'] = json.dumps(triggers)
            return response
        
        form = WorkSpaceForm(user=request.user,instance=workspace, data=request.POST or None)
        if request.method == 'POST' and form.is_valid():
            members = form.cleaned_data.get('members')
            
            members_list = list(members)
            members_list.append(workspace.created_by)
            
            # Save form but don't commit to DB yet
            instance = form.save(commit=False)
            
            # Manually set the modified members list
            instance.save()
            instance.members.set(members_list)  # assuming it's a ManyToMany field

            response = render(request, "workspace/components/workspace_card.html", {"workspace": instance})
            triggers = {'workspaceEdited':{'message':'Workspace Edited', 'level':'info'}}
            triggers["showToast"] = {"message":"Workspace Edited", "level":"success"}
            response['HX-Trigger'] = json.dumps(triggers)
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
            response = HttpResponseClientRefresh()
            triggers = {}
            triggers["showToast"] = {"message":"Board Deleted", "level":"danger"}
            response['HX-Trigger'] = json.dumps(triggers)
            return response
            
        form = BoardForm(workspace=board.workspace,user=request.user, instance=board, data=request.POST or None)
        if request.method == 'POST' and form.is_valid():
            members = form.cleaned_data.get('members')
            
            members_list = list(members)
            members_list.append(board.created_by)

            instance:Board = form.save(commit=False)
            # Manually set the modified members list
            instance.save()
            instance.members.set(members_list)  # assuming it's a ManyToMany field

            response = render(request,'boards/components/board_list_item.html',{'board':instance})
            triggers = {}
            triggers["closeModal"] = {"modal_id": "close_editBoardModal", "level": "info"}
            triggers["showToast"] = {"message":"Board Detail Edited", "level":"success"}
            response['HX-Trigger'] = json.dumps(triggers)
            return response
        return render(request,'boards/components/board_edit.html',{'form':form})
    except Exception as e:
        logger.exception(stack_info=False, msg=str(e))
        if request.htmx:
            redirect_url = reverse('workspace:index')
            return HttpResponseClientRedirect(redirect_to=redirect_url)
        return redirect('workspace:index')




@login_required
def workspace_invite_view(request, workspace_uuid):
    try:
        workspace = Workspace.objects.get(uuid=workspace_uuid)
        user = request.user

        if user in workspace.members.all():
            # Already a member, redirect to workspace index
            return redirect('workspace:get_workspace_boards', workspace_id=workspace.id)

        if request.method == 'POST':
            # User confirms joining
            workspace.members.add(user)
            return redirect('workspace:get_workspace_boards', workspace_id=workspace.id)

        # Show confirmation page
        return render(request, 'workspace/invite_confirmation.html', {
            'workspace': workspace
        })
    except Workspace.DoesNotExist:
        return redirect('workspace:index')