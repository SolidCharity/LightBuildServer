from django.urls import path

from . import views

app_name = 'builder'
urlpatterns = [
    path('triggerbuild/<str:user>/<str:project>/<str:package>/<str:branchname>/<str:lxcdistro>/<str:lxcrelease>/<str:lxcarch>', views.buildtarget, name='triggerbuild'),
]
