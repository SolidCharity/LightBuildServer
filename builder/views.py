import sys

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from django.contrib.auth.models import User
from lib.LightBuildServer import LightBuildServer
from projects.models import Package, Project
from machines import views as machine_view

@login_required
def buildtarget(request, user, project, package, branchname, lxcdistro, lxcrelease, lxcarch):
    project = Project.objects.get(user=User.objects.get(username__exact=user), name=project)

    # is the correct user logged in? or the admin?
    if not project.visible and not request.user.is_staff:
        if request.user != project.user:
            raise Exception("you do not have permission for this project")

    # start building
    LBS = LightBuildServer()
    if LBS.BuildProjectWithBranch(project, package, branchname, lxcdistro, lxcrelease, lxcarch):
        return machine_view.monitor(request, successmessage="Build job has been added to the queue")
    else:
        return machine_view.monitor(request, errormessage="This build job is already in the queue")

@login_required
def cancelbuild(request, user, project, package, branchname, lxcdistro, lxcrelease, lxcarch):
    project = Project.objects.get(user=User.objects.get(username__exact=user), name=project)

    # is the correct user logged in? or the admin?
    if not project.visible and not request.user.is_staff:
        if request.user != project.user:
            raise Exception("you do not have permission for this project")

    # stop building
    try:
        LBS = LightBuildServer()
        LBS.CancelPlannedBuild(project, package, branchname, lxcdistro, lxcrelease, lxcarch)
        return machine_view.monitor(request, successmessage="Build job has been removed from the queue")
    except:
        print("Unexpected error:", sys.exc_info()[0])
        print(sys.exc_info())
        return machine_view.monitor(request, errormessage="Unexpected error")
