from django.urls import path

from . import views

app_name = 'projects'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('<str:user>/<str:project>/<str:branch>/', views.ProjectView.as_view(), name='project'),
    path('<str:user>/<str:project>/package/<str:package>/', views.PackageView.as_view(), name='package')
]
