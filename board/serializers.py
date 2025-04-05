# serializers.py

from rest_framework import serializers
from accounts.models import Users as User
from board.models import Board, Column, Task, SubTask


class SubTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubTask
        fields = '__all__'


class TaskSerializer(serializers.ModelSerializer):
    subtasks = SubTaskSerializer(many=True, read_only=True)
    
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ('column','created_by', 'created_at')


class ColumnSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Column
        fields = '__all__'
        read_only_fields = ('board','created_by', 'created_at')


class BoardSerializer(serializers.ModelSerializer):
    columns = ColumnSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        read_only_fields = ('created_by', 'created_at')
        fields = '__all__'
        extra_kwargs = {
            'members': {'required': False}
        }
