from django.shortcuts import render

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from board.models import Board, Column, Task, SubTask
from board.permissions import IsBoardMemberOrReadOnly
from board.serializers import BoardSerializer, ColumnSerializer, TaskSerializer, SubTaskSerializer, BoardListSerializer


from task_manager.logger import logger


from django_filters.rest_framework import DjangoFilterBackend




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



