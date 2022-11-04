from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from django.contrib.auth.models import User
from lib.LightBuildServer import LightBuildServer
from projects.models import Package, Project

@login_required
def buildtarget(request, user, project, package, branchname, lxcdistro, lxcrelease, lxcarch):
    project = Project.objects.get(user=User.objects.get(username__exact=user), name=project)

    # is the correct user logged in? or the admin?
    if not project.visible and not request.user.is_staff:
        if request.user != project.user:
            raise Exception("you do not have permission for this project")

    # start building
    LBS = LightBuildServer()
    LBS.BuildProjectWithBranch(project, package, branchname, lxcdistro, lxcrelease, lxcarch)

    # TODO: redirect to livelog
    return redirect('/')