from django.urls import path, include
from accounts import views

urlpatterns = [
    path('login/', views.email_login, name='login-user'),
    path('logout/', views.logout_user, name='logout-user'),
    path('api-auth/', include('rest_framework.urls')),
]