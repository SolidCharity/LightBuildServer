from django.urls import path

from . import views

app_name = 'machines'
urlpatterns = [
    path('', views.monitor, name='monitor'),
    path('reset/<str:machine_name>', views.reset, name='reset'),
]
