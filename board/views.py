from django.shortcuts import render

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import get_object_or_404

from board.models import Board, Column, Task, SubTask
from board.permissions import IsBoardMemberOrReadOnly
from board.serializers import BoardSerializer, ColumnSerializer, TaskSerializer, SubTaskSerializer


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


    def retrieve(self, request, *args, **kwargs):
        logger.info(f'{kwargs=}')
        instance = self.get_object()
        logger.info(f'{instance=}')

        if not instance:
            return Response({"detail": "Column not found"}, status=404)

        # Return the column details using the serializer
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a specific column for a specific board.
        """
        instance = self.get_object()

        if not instance:
            return Response({"detail": "Column not found"}, status=404)

        self.perform_destroy(instance)
        
        return Response(status=204)
    
    def get_columns(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


    

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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


    def retrieve(self, request, *args, **kwargs):
        
        instance = self.get_object()

        if not instance:
            return Response({"detail": "Task not found"}, status=404)
        
        # Return the column details using the serializer
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a specific column for a specific board.
        """
        instance = self.get_object()

        if not instance:
            return Response({"detail": "Task not found"}, status=404)

        self.perform_destroy(instance)
        return Response(status=204)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

class SubTaskViewSet(viewsets.ModelViewSet):
    queryset = SubTask.objects.all()
    serializer_class = SubTaskSerializer
