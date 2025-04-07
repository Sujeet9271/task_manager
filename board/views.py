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

from board.forms import TaskCreateForm, TaskForm
from board.models import Board, Column, Task, SubTask
from board.permissions import IsBoardMemberOrReadOnly
from board.serializers import BoardSerializer, ColumnSerializer, TaskSerializer, SubTaskSerializer, BoardListSerializer


from task_manager.logger import logger


from django_filters.rest_framework import DjangoFilterBackend

@login_required
def index(request):
    boards = Board.objects.filter(members=request.user).exclude(is_deleted=True)
    return render(request, 'boards/index.html', {'boards': boards})

@login_required
def board_view(request, board_id):
    board = get_object_or_404(Board, pk=board_id)
    return render(request, 'boards/components/board.html', {'board': board})

@require_http_methods(['GET', 'POST'])
@login_required
def create_column(request, board_id):
    board = get_object_or_404(Board, pk=board_id)
    if request.method == 'POST':
        column = Column.objects.create(name=request.POST.get('name'), board=board, created_by=request.user)
        response = render(request,'boards/components/board_list_item.html',{'column':column,'board_id':board_id})
        if request.htmx:
            board_url = reverse('board:board-view',kwargs={'board_id':board_id}) 
            response['HX-Trigger']=json.dumps({"reloadBoard":{"message":board_url,"level":"info"}})
        return response
    return render(request, 'boards/components/board_create.html', {'board': board,})

@require_http_methods(['DELETE'])
@login_required
def delete_column(request, board_id, column_id):
    column = get_object_or_404(Column, pk=column_id, board_id=board_id)
    column.delete()    
    response = JsonResponse(data={'detail':'Column Deleted'},safe=False,status=200)  # Renders nothing for removal
    if request.htmx:
        response['HX-Trigger'] = json.dumps({"columnDeleted": {"level": "info", "board_list_item": f"board_{board_id}_column_{column_id}"}})
    return response


@require_GET
@login_required
def get_task_lists(request, board_id, column_id):
    column = get_object_or_404(Column, pk=column_id, board_id=board_id)
    return render(request, 'boards/components/column.html', {'column': column})


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
        response['HX-Trigger'] = json.dumps({"taskCreated": {"get_task_lists": reverse('board:get_task_lists', kwargs={'board_id': board_id,'column_id':column_id}),'column_id':column_id,'board_id':board_id, "level": "info"}})
        return response
    return render(request,'boards/components/create.html',{'board_id':board_id,'column_id':column_id, 'form':form})


@require_http_methods(['GET','POST'])
@login_required
def edit_task(request, board_id, column_id, task_id):
    task = get_object_or_404(Task, pk=task_id, column_id=column_id, column__board_id=board_id)
    form = TaskForm(instance=task, data=request.POST or None)
    if request.method=='POST':
        if form.is_valid():
            task = form.save(commit=False)
            task.updated_by = request.user
            task.save()
            if request.htmx:
                response = HttpResponse()
                response['HX-Trigger'] = json.dumps({"taskEdited": {"message": reverse('board:board-view', kwargs={'board_id': board_id}), "level": "info"}})
                return response
    return render(request,'boards/components/edit.html',{'task':task,'board_id':board_id,'column_id':column_id, 'form':form})


@require_http_methods(['DELETE'])
@login_required
def delete_task(request, board_id, column_id, task_id):
    task = get_object_or_404(Task, pk=task_id, column_id=column_id, column__board_id=board_id)
    task.delete()
    return JsonResponse(data={'detail':'Task Deleted'},safe=False,status=200)  # Renders nothing for removal



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

    
class SubTaskViewSet(viewsets.ModelViewSet):
    queryset = SubTask.objects.all()
    serializer_class = SubTaskSerializer


    def get_queryset(self):
        """
        Return columns for the specified board.
        """
        board_id = self.kwargs.get('board_id')
        if board_id:
            column_id = self.kwargs.get('column_id')
            if column_id:
                task_id = self.kwargs.get('task_id')
                if task_id:
                    return SubTask.objects.filter(task__column__board_id=board_id, task__column_id=column_id, task_id=task_id)
                return SubTask.objects.filter(task__column__board_id=board_id,task__column_id=column_id)
            return SubTask.objects.filter(task__column__board_id=board_id)
        return super().get_queryset()
    

    def perform_create(self, serializer):
        board_id = self.kwargs.get('board_id')
        column_id = self.kwargs.get('column_id')
        task_id = self.kwargs.get('task_id')
        task = Task.objects.get(column__board_id=board_id, column_id=column_id, id=task_id)
        instance:SubTask = serializer.save(task=task, created_by=self.request.user)
        instance.assigned_to.add(self.request.user)


    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'deleted_at'])


    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)



