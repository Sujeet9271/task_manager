from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BoardViewSet, ColumnViewSet, TaskViewSet, SubTaskViewSet

router = DefaultRouter()
router.register('boards', BoardViewSet)

urlpatterns = [
    # path('api/', include(router.urls)),
    path('api/boards/', BoardViewSet.as_view({'get': 'list', 'post':'create'}), name='board_list'),
    path('api/boards/<int:pk>/', BoardViewSet.as_view({'get': 'retrieve', 'delete':'destroy', 'put':'update', 'patch':'partial_update'}), name='board_detail'),

    path('api/boards/<int:board_id>/columns/', ColumnViewSet.as_view({'post': 'create', 'get':'list'}), name='create_column'),
    path('api/boards/<int:board_id>/columns/<int:pk>/', ColumnViewSet.as_view({'get': 'retrieve', 'delete': 'destroy', 'put':'update', 'patch':'partial_update', }), name='column_detail'),
    
    path('api/boards/<int:board_id>/columns/<int:column_id>/tasks/', TaskViewSet.as_view({'post':'create'}), name='create_task'),
    path('api/boards/<int:board_id>/columns/<int:column_id>/tasks/<int:pk>/', TaskViewSet.as_view({'get': 'retrieve', 'delete': 'destroy', 'put':'update', 'patch':'partial_update', }), name='task_detail'),
    
    path('api/boards/<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/subtasks/', SubTaskViewSet.as_view({'post': 'create'}), name='create_subtask'),
    path('api/boards/<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/subtasks/<int:pk>/', SubTaskViewSet.as_view({'get': 'retrieve', 'delete': 'destroy', 'put':'update', 'patch':'partial_update'}), name='subtask_detail'),
]