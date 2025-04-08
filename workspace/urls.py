from django.urls import path, include
from workspace import views


urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.workspace_create, name='workspace_create'),
    path('<int:workspace_id>/', views.get_workspace_boards, name='get_workspace_boards'),
    path('<int:workspace_id>/actions', views.workspace_actions, name='workspace_actions'),
]