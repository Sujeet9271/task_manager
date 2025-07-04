from django.urls import path, include
from board import views

urlpatterns = [
    path('create/', views.create_board, name='board-create'),
    path('<int:board_id>/', views.board_view, name='board-view'),
    path('invite/<uuid:board_uuid>/', views.board_invite_view, name='board-invite'),
    path('search/', views.search_boards, name='board-search'),
    path('<int:board_id>/reports/', views.board_reports, name='board-reports'),
    path('<int:board_id>/create_column/', views.create_column, name='column-create'),
    path('<int:board_id>/columns/', views.load_columns, name='board-columns'),
    path('<int:board_id>/columns/<int:column_id>/', views.get_task_lists, name='get_task_lists'),
    path('<int:board_id>/columns/<int:column_id>/update_name/', views.update_column_name, name='update_column_name'),
    path('<int:board_id>/columns/<int:column_id>/delete/', views.delete_column, name='column-delete'),
    path('<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/detail/', views.detail_task, name='task-detail'),
    path('<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/move/', views.task_move, name='task-move'),
    path('<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/history/', views.history_task, name='task-history'),
    path('<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/edit/', views.edit_task, name='task-edit'),
    path('<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/delete/', views.delete_task, name='task-delete'),
    path('<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/toggle/', views.task_status_toggle, name='task-status-toggle'),
    path('<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/sub_tasks/', views.get_sub_task_lists, name='get_sub_task_list'),
    path('<int:board_id>/columns/<int:column_id>/tasks/<int:task_id>/sub_tasks/create/', views.create_sub_task, name='sub-task-create'),
    
    path('<int:board_id>/tasks/create/', views.create_task, name='task-create'),
    path('tasks/<int:task_id>/add_comment/', views.add_comment, name='add_comment'),
    path('tasks/<int:task_id>/move/', views.move_task, name='task-move'),

    # path('api/', include(router.urls)),
    path('api/boards/', views.BoardViewSet.as_view({'get': 'list', 'post':'create'}), name='board_list'),
    path('api/boards/<int:pk>/', views.BoardViewSet.as_view({'get': 'retrieve', 'delete':'destroy', 'put':'update', 'patch':'partial_update'}), name='board_detail'),

    path('api/boards/<int:board_id>/columns/', views.ColumnViewSet.as_view({'post': 'create', 'get':'list'}), name='create_column'),
    path('api/boards/<int:board_id>/columns/<int:pk>/', views.ColumnViewSet.as_view({'get': 'retrieve', 'delete': 'destroy', 'put':'update', 'patch':'partial_update', }), name='column_detail'),
    
    path('api/boards/<int:board_id>/columns/<int:column_id>/tasks/', views.TaskViewSet.as_view({'post':'create'}), name='create_task'),
    path('api/boards/<int:board_id>/columns/<int:column_id>/tasks/<int:pk>/', views.TaskViewSet.as_view({'get': 'retrieve', 'delete': 'destroy', 'put':'update', 'patch':'partial_update', }), name='task_detail'),
]