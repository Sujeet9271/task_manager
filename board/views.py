from django.shortcuts import render

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from board.models import Board, Column, Task, SubTask
from board.permissions import IsBoardMemberOrReadOnly
from board.serializers import BoardSerializer, ColumnSerializer, TaskSerializer, SubTaskSerializer

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
        """
        Save the new board with the current user as the creator.
        """
        serializer.save(created_by=self.request.user)


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
        """
        Save the new column to the specified board.
        """
        board_id = self.kwargs.get('board_id')
        board = Board.objects.get(id=board_id)
        serializer.save(board=board, created_by=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific column for a specific board.
        """
        board_id = kwargs.get('board_id')
        column_id = kwargs.get('column_id')
        
        # Fetch the board to ensure it's valid
        board = Board.objects.get(id=board_id)

        # Fetch the column for the given board
        column = Column.objects.filter(board=board, id=column_id).first()

        if not column:
            return Response({"detail": "Column not found"}, status=404)

        # Return the column details using the serializer
        serializer = self.get_serializer(column)
        return Response(serializer.data)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['column', 'assigned_to']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'created_at']


class SubTaskViewSet(viewsets.ModelViewSet):
    queryset = SubTask.objects.all()
    serializer_class = SubTaskSerializer
