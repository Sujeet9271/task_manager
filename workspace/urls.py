from django.urls import path, include
from workspace import views


urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.workspace_create, name='workspace_create'),
    path('<int:workspace_id>/', views.get_workspace_boards, name='get_workspace_boards'),
    path('<int:workspace_id>/actions', views.workspace_actions, name='workspace_actions'),
    path('<int:workspace_id>/board/<int:board_id>/board_actions/', views.board_actions, name='board-actions'),
    path('invite/<uuid:workspace_uuid>/', views.workspace_invite_view, name='workspace-invite'),
]