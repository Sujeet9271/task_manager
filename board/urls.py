from django.urls import path, include
from board import views

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create_board, name='board-create'),
    path('<int:board_id>/', views.board_view, name='board-view'),
    path('<int:board_id>/create_column/', views.create_column, name='column-create'),
    path('<int:board_id>/columns/<int:column_id>/', views.get_task_lists, name='get_task_lists'),
    path('<int:board_id>/columns/<int:column_id>/delete/', views.delete_column, name='column-delete'),
    path('<int:board_id>/columns/<int:column_id>/tasks/create/', views.create_task, name='task-create'),
    path('<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/edit/', views.edit_task, name='task-edit'),
    path('<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/delete/', views.delete_task, name='task-delete'),


    # path('api/', include(router.urls)),
    path('api/boards/', views.BoardViewSet.as_view({'get': 'list', 'post':'create'}), name='board_list'),
    path('api/boards/<int:pk>/', views.BoardViewSet.as_view({'get': 'retrieve', 'delete':'destroy', 'put':'update', 'patch':'partial_update'}), name='board_detail'),

    path('api/boards/<int:board_id>/columns/', views.ColumnViewSet.as_view({'post': 'create', 'get':'list'}), name='create_column'),
    path('api/boards/<int:board_id>/columns/<int:pk>/', views.ColumnViewSet.as_view({'get': 'retrieve', 'delete': 'destroy', 'put':'update', 'patch':'partial_update', }), name='column_detail'),
    
    path('api/boards/<int:board_id>/columns/<int:column_id>/tasks/', views.TaskViewSet.as_view({'post':'create'}), name='create_task'),
    path('api/boards/<int:board_id>/columns/<int:column_id>/tasks/<int:pk>/', views.TaskViewSet.as_view({'get': 'retrieve', 'delete': 'destroy', 'put':'update', 'patch':'partial_update', }), name='task_detail'),
    
    path('api/boards/<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/subtasks/', views.SubTaskViewSet.as_view({'post': 'create'}), name='create_subtask'),
    path('api/boards/<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/subtasks/<int:pk>/', views.SubTaskViewSet.as_view({'get': 'retrieve', 'delete': 'destroy', 'put':'update', 'patch':'partial_update'}), name='subtask_detail'),
]