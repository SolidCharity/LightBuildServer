"""lbs URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
from django.contrib.auth.views import LoginView, logout_then_login
from django.views.generic import RedirectView
from django.urls import include, path

urlpatterns = [
    path('', RedirectView.as_view(url='projects/')),
    path('admin/', admin.site.urls),
    path('accounts/profile/', RedirectView.as_view(url='/')),
    path('accounts/login/', LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('accounts/logout/', logout_then_login, {'login_url': '/accounts/login/'}, name='logout'),
    path('projects/', include('projects.urls')),
    path('machines/', include('machines.urls')),
]
