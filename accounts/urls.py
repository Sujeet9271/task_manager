from django.urls import path, include
from accounts import views


urlpatterns = [
    path('register/', views.register_user, name='register-user'),
    path('register/success/', views.account_created_msg, name='account_created_msg'),
    path('login/', views.email_login, name='login-user'),
    path('logout/', views.logout_user, name='logout-user'),
    path('api-auth/', include('rest_framework.urls')),
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'), 
]