"""
URL configuration for task_manager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path, include
from django.contrib.auth.decorators import login_required
from board import urls as board_urls
from accounts import urls as accounts_urls
from notifications import urls as notification_urls
from task_manager import settings
from workspace import urls as workspace_urls
from django.conf.urls.static import static


@login_required
def index(request):
    return redirect('workspace:index')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('hijack/', include('hijack.urls')),
    path('',index, name='index'),
    path('auth/', include((accounts_urls, 'accounts'), namespace='accounts')),
    path('board/', include((board_urls, 'board'), namespace='board')),
    path('notification/', include((notification_urls, 'notifications'), namespace='notifications')),
    path('workspace/', include((workspace_urls, 'workspace'), namespace='workspace')),
]



if settings.DEBUG:
    urlpatterns+=static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
