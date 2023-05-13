"""
URL configuration for optimuspy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from web import views
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'tasks', views.TaskViewSet)
router.register(r'benchmarks', views.BenchmarkViewSet)
router.register(r'results', views.ResultViewSet)
router.register(r'errors', views.CompilerErrorViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('api/', include(router.urls)),
    path('accounts/login/', views.LogIn.as_view(), name='login'),
    path('accounts/signup/', views.SignUp.as_view(), name='signup'),
    path('accounts/logout/', views.ulogout, name='logout'),
    path('tasks/', views.tasks_list, name='list'),
    path('tasks/submit/', views.tasks_submit, name='submit'),
    path('tasks/<int:tid>/result', views.tasks_result, name='result'),
    path('tasks/<int:tid>/signature/', views.tasks_signature, name='signature'),
    path('tasks/<int:tid>/ready/', views.tasks_ready, name='ready'),
    path('tasks/<int:tid>/stats/', views.tasks_stats, name='stats'),
    path('download/<int:rid>/', views.result_download, name='download'),
    path('token-get/', obtain_auth_token, name='token-get')
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
