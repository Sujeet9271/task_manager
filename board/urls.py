from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BoardViewSet, ColumnViewSet, TaskViewSet, SubTaskViewSet

router = DefaultRouter()
router.register('boards', BoardViewSet)
router.register(r'boards/(?P<board_id>\d+)/columns', ColumnViewSet, basename='board-columns')
router.register('tasks', TaskViewSet)
router.register('subtasks', SubTaskViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/boards/<int:board_id>/columns/<int:column_id>/', ColumnViewSet.as_view({'get': 'retrieve'}), name='column-detail'),
]