import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from accounts.models import Users
from board.forms import CommentForm, SubTaskCreateForm, TaskCreateForm, TaskForm
from board.models import Attachment, Board, Column, Comments, Task
from board.permissions import IsBoardMemberOrReadOnly
from board.serializers import BoardSerializer, ColumnSerializer, TaskSerializer, BoardListSerializer


from task_manager.logger import logger


from django_filters.rest_framework import DjangoFilterBackend

from workspace.models import Workspace


@login_required
def board_view(request, board_id):
    board:Board = get_object_or_404(Board, pk=board_id, members=request.user)
    context={'board':board}
    if request.htmx:
        response = render(request, 'boards/components/board.html', context)
        response['HX-Trigger'] = json.dumps({"boardLoaded": {"board_id":  board_id, "level": "info"}})
    else:
        context['boards'] = Board.objects.filter(members=request.user).exclude(is_deleted=True)
        context['workspace_id'] = board.workspace_id
        response = render(request, 'boards/index.html', context)
    return response

@require_http_methods(['POST'])
@login_required
def create_board(request):
    logger.info(request.session.get('workspace'))
    data = {
        'name': request.POST.get('name'),
        'description': request.POST.get('description'),
        'created_by': request.user,
    }
    if request.POST.get('workspace_id'):
        data['workspace']=Workspace.objects.filter(id=request.POST['workspace_id']).first()
    board = Board.objects.create(**data)
    if board.workspace:
        board.members.add(*board.workspace.members.all())
    else:
        board.members.add(request.user)
    response = render(request,'boards/components/board_list_item.html',{'board':board})
    if request.htmx:
        board_url = reverse('board:board-view',kwargs={'board_id':board.id}) 
        response['HX-Trigger']=json.dumps({"boardCreated":{"message":board_url,"level":"info"}})
    return response

@require_http_methods(['GET', 'POST'])
@login_required
def create_column(request, board_id):
    board = get_object_or_404(Board, pk=board_id)
    if request.method == 'POST':
        column = Column.objects.create(name=request.POST.get('name'), board=board, created_by=request.user)
        response = render(request,'boards/components/column_list_item.html',{'column':column,'board_id':board_id})
        if request.htmx:
            board_url = reverse('board:board-view',kwargs={'board_id':board_id}) 
            response['HX-Trigger']=json.dumps({"reloadBoard":{"message":board_url,"level":"info"}})
        return response
    return render(request, 'boards/components/column_create.html', {'board': board,})

@require_http_methods(['POST'])
@login_required
def update_column_name(request, board_id, column_id):
    column = get_object_or_404(Column, pk=column_id, board_id=board_id)
    name = request.POST.get('column_name')
    if name:
        column.name = name
        column.save(update_fields=['name'])
    response = JsonResponse(data={'detail':'Column Name Updated'},safe=False,status=200)  # Renders nothing for removal
    if request.htmx:
        response['HX-Trigger'] = json.dumps({"columnUpdated": {"level": "info","column_id":column_id,"board_id":board_id, "column_name": column.name}})
    return response


@require_http_methods(['DELETE'])
@login_required
def delete_column(request, board_id, column_id):
    column = get_object_or_404(Column, pk=column_id, board_id=board_id)
    column.delete()    
    response = JsonResponse(data={'detail':'Column Deleted'},safe=False,status=200)  # Renders nothing for removal
    if request.htmx:
        response['HX-Trigger'] = json.dumps({"columnDeleted": {"level": "info","create_column_url":reverse('board:column-create',kwargs={'board_id':board_id}), "column_list_item": f"board_{board_id}_column_{column_id}"}})
    return response


@require_GET
@login_required
def get_task_lists(request, board_id, column_id):
    column = get_object_or_404(Column, pk=column_id, board_id=board_id)
    tasks = column.tasks.filter(assigned_to=request.user, parent_task__isnull=True) if not request.user.is_staff else column.tasks.filter(parent_task__isnull=True)
    return render(request, 'boards/components/column.html', {'column': column,'tasks':tasks})



def sub_task_list(user:Users,task:Task,context:dict=dict):
    context['task'] = task
    context['sub_tasks'] = task.sub_tasks.filter(assigned_to=user) if not user.is_staff else task.sub_tasks.all()
    return context



@require_GET
@login_required
def get_sub_task_lists(request, board_id, column_id, task_id):
    context={'board_id':board_id, 'column_id':column_id, 'task_id':task_id}
    task = get_object_or_404(Task, pk=task_id, column_id=column_id)
    context = sub_task_list(user=request.user,task=task, context=context)
    return render(request, 'boards/components/sub_task_list.html', context)


@require_http_methods(['GET','POST'])
@login_required
def create_sub_task(request, board_id, column_id, task_id):
    task = get_object_or_404(Task, pk=task_id)
    context={
        'task_id':task_id,
        'column_id':column_id,
        'board_id':board_id
    }
    form = SubTaskCreateForm(user=request.user,task=task,data=request.POST or None)
    if request.method=='POST' and form.is_valid():
        instance:Task = form.save(commit=False)
        instance.parent_task = task
        instance.column = task.column
        instance.created_by = request.user
        instance.save()
        form.save_m2m()
        instance.assigned_to.add(request.user)
        context = sub_task_list(user=request.user,task=task, context=context)
        response = render(request, 'boards/components/sub_task_list.html',context)
        return response
    context['form'] = form
    return render(request,'boards/components/sub_task_create.html',context)

@require_POST
@login_required
def create_task(request, board_id, column_id):
    column = get_object_or_404(Column, pk=column_id, board_id=board_id)
    form = TaskCreateForm(data=request.POST)
    if form.is_valid():
        instance:Task = form.save(commit=False)
        instance.column = column
        instance.created_by = request.user
        instance.save()
        instance.assigned_to.add(request.user)
        response = render(request, 'boards/components/task_card.html', {'board_id': board_id, 'task': instance})
        response['HX-Trigger'] = json.dumps({"reloadTaskList": {"get_task_lists": reverse('board:get_task_lists', kwargs={'board_id': board_id,'column_id':column_id}),'column_id':column_id,'board_id':board_id, "level": "info"}})
        return response
    return render(request,'boards/components/create.html',{'board_id':board_id,'column_id':column_id, 'form':form})


@require_http_methods(['GET','POST'])
@login_required
def edit_task(request, board_id, column_id, task_id):
    task = get_object_or_404(Task, pk=task_id, column_id=column_id, column__board_id=board_id)
    form = TaskForm(workspace=task.column.board.workspace, user=request.user,instance=task, data=request.POST or None)
    if request.method=='POST':
        if form.is_valid():
            task = form.save(commit=False)
            task.updated_by = request.user
            task.save()
            form.save_m2m()

            files = request.FILES.getlist('attachments')
            urls = request.POST.getlist('urls')
            url_names = request.POST.getlist('url_names')
            attachment_list = []
            # Upload files
            for file in files:
                attachment_list.append(
                Attachment(
                    workspace=form.workspace,
                    task=task,
                    file=file,
                    type='file',
                    uploaded_by=request.user
                ))

            # Store links
            for url, name in zip(urls, url_names):
                if url.strip():  # skip blanks
                    attachment_list.append(
                    Attachment(
                        workspace=form.workspace,
                        task=task,
                        type='url',
                        url=url.strip(),
                        name=name.strip() or None,
                        uploaded_by=request.user
                    ))

            if attachment_list:
                Attachment.objects.bulk_create(attachment_list)
            if request.htmx:
                response = HttpResponse()
                response['HX-Trigger'] = json.dumps({"taskEdited": {"message": reverse('board:board-view', kwargs={'board_id': board_id}), "level": "info"}})
                return response
    
    comments = Comments.objects.select_related('added_by').filter(task=task)
    comment_form = CommentForm()
    return render(request,'boards/components/edit.html',{'task':task,'board_id':board_id,'column_id':column_id, 'form':form, "comments":comments,"comment_form":comment_form})

@require_http_methods(['POST'])
@login_required
def add_comment(request, task_id):
    task = get_object_or_404(Task, pk=task_id,)
    form = CommentForm(data=request.POST)
    if form.is_valid():
        comment:Comments = form.save(commit=False)
        comment.added_by = request.user
        comment.task = task
        comment.save()
        response = render(request,'boards/components/comment.html',{'comment':comment})
        response['HX-Trigger'] = 'commentAdded'
        return response
    return JsonResponse(data=form.errors.as_json(), status=400)


@require_http_methods(['POST'])
@login_required
def task_status_toggle(request, board_id, column_id, task_id):
    task:Task = get_object_or_404(Task, pk=task_id, column_id=column_id, column__board_id=board_id)
    if task.is_complete:
        task.is_complete = False
    else:
        task.is_complete = True
    task.save(update_fields=['is_complete'])
    response = render(request,'boards/components/task_card.html',{'task':task,"board_id":board_id,"column_id":column_id})
    return response

@require_http_methods(['DELETE'])
@login_required
def delete_task(request, board_id, column_id, task_id):
    task = get_object_or_404(Task, pk=task_id, column_id=column_id, column__board_id=board_id)
    task.delete()
    return JsonResponse(data={'detail':'Task Deleted'},safe=False,status=200)  # Renders nothing for removal

@require_POST
@login_required
def move_task(request, task_id):
    new_column_id = request.POST.get('column_id')
    try:
        task = Task.objects.get(id=task_id)
        old_column_id = task.column_id
        column = Column.objects.get(id=new_column_id)
        task.column = column
        task.save()
        response = JsonResponse({'success': True})
        response['HX-Trigger'] = json.dumps({"reloadTaskList": {"get_task_lists": reverse('board:get_task_lists', kwargs={'board_id': column.board_id,'column_id':old_column_id}),'column_id':old_column_id,'board_id':column.board_id, "level": "info"}})
        return response
    except (Task.DoesNotExist, Column.DoesNotExist):
        return JsonResponse({'success': False}, status=400)

class BoardViewSet(viewsets.ModelViewSet):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    permission_classes = [IsBoardMemberOrReadOnly]
    

    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        board = self.get_object()
        tasks = Task.objects.filter(column__board=board)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        instance.members.add(self.request.user)  # Add the creator as a member of the board

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'deleted_at'])

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = BoardListSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        logger.info(f'{kwargs=}')
        instance = self.get_object()
        logger.info(f'{instance=}')

        if not instance:
            return Response({"detail": "Board not found"}, status=404)

        # Return the column details using the serializer
        serializer = BoardSerializer(instance)
        return Response(serializer.data)
    
    


class ColumnViewSet(viewsets.ModelViewSet):
    queryset = Column.objects.all()
    serializer_class = ColumnSerializer

    def get_queryset(self):
        """
        Return columns for the specified board.
        """
        board_id = self.kwargs.get('board_id')
        if board_id:
            return Column.objects.filter(board_id=board_id)
        return super().get_queryset()
    

    def perform_create(self, serializer):
        board_id = self.kwargs.get('board_id')
        board = Board.objects.get(id=board_id)
        serializer.save(board=board, created_by=self.request.user)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'deleted_at'])

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['column', 'assigned_to']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'created_at']

    def get_queryset(self):
        """
        Return columns for the specified board.
        """
        board_id = self.kwargs.get('board_id')
        if board_id:
            column_id = self.kwargs.get('column_id')
            if column_id:
                return Task.objects.filter(column__board_id=board_id,column_id=column_id)
            return Task.objects.filter(column__board_id=board_id)
        return super().get_queryset()
    

    def perform_create(self, serializer):
        board_id = self.kwargs.get('board_id')
        column_id = self.kwargs.get('column_id')
        column = Column.objects.get(id=column_id, board_id=board_id)
        instance:Task = serializer.save(column=column, created_by=self.request.user)
        instance.assigned_to.add(self.request.user)


    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'deleted_at'])


    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
