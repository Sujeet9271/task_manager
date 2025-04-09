from django.urls import path, include
from notifications import views

urlpatterns = [
    path("", views.notifications, name="notifications"),
    path("<int:id>/", views.read_notification, name="read_notification")
]