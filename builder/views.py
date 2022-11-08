import sys

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate

from lib.Logger import Logger
from lib.LightBuildServer import LightBuildServer

from django.contrib.auth.models import User
from projects.models import Package, Project
from builder.models import Build

from machines import views as machine_view

def buildtarget(request, user, project, package, branchname, distro, release, arch, authuser=None, authpwd =None):
    project = Project.objects.get(user=User.objects.get(username__exact=user), name=project)

    if authuser and authpwd:
        currentuser = authenticate(username=authuser, password=authpwd)
    else:
        currentuser = request.user

    # is the correct user logged in? or the admin?
    if currentuser and not project.visible and not currentuser.is_staff:
        if currentuser != project.user:
            currentuser = None

    if not currentuser or currentuser.is_anonymous:
        return machine_view.monitor(request, errormessage="You do not have permission for this project")

    # start building
    LBS = LightBuildServer()
    if LBS.BuildProjectWithBranch(project, package, branchname, distro, release, arch):
        return machine_view.monitor(request, successmessage="Build job has been added to the queue")
    else:
        return machine_view.monitor(request, errormessage="This build job is already in the queue")

@login_required
def cancelbuild(request, user, project, package, branchname, distro, release, arch):
    project = Project.objects.get(user=User.objects.get(username__exact=user), name=project)

    # is the correct user logged in? or the admin?
    if not project.visible and not request.user.is_staff:
        if request.user != project.user:
            raise Exception("you do not have permission for this project")

    # stop building
    try:
        LBS = LightBuildServer()
        LBS.CancelPlannedBuild(project, package, branchname, distro, release, arch)
        return machine_view.monitor(request, successmessage="Build job has been removed from the queue")
    except:
        print("Unexpected error:", sys.exc_info()[0])
        print(sys.exc_info())
        return machine_view.monitor(request, errormessage="Unexpected error")

def viewlog(request, user, project, package, branchname, distro, release, arch, buildid):
    build = Build.objects.get(pk=buildid)

    project = Project.objects.filter(user=build.user, name=build.project).first()

    # is the correct user logged in? or the admin?
    if not project.visible and not request.user.is_staff:
        if request.user != project.user:
            raise Exception("you do not have permission for this project")

    content = Logger().getLog(build)

    return render(request, "builder/log.html",
        { 'buildresult': content,
         'timeoutInSeconds': -1,
         'build_descr': f"{build.user.username}/{build.project}/{build.package}/{build.branchname}",
        })

def livelog(request, user, project, package, branchname, distro, release, arch, buildid):
    build = Build.objects.get(pk=buildid)

    project = Project.objects.get(user=build.user, name=build.project)

    # is the correct user logged in? or the admin?
    if not project.visible and not request.user.is_staff:
        if request.user != project.user:
            raise Exception("you do not have permission for this project")

    lbs = LightBuildServer()
    (content, timeout) = lbs.LiveLog(build)

    return render(request, "builder/log.html",
        { 'buildresult': content,
         'timeoutInSeconds': timeout,
         'build_descr': f"{build.user.username}/{build.project}/{build.package}/{build.branchname}",
        })
