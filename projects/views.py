from itertools import chain
from django.views import generic
from django.shortcuts import render
from django.contrib.auth.models import User

from lib.Logger import Logger
from lib.LightBuildServer import LightBuildServer

from .models import Project, Package


class IndexView(generic.ListView):
    template_name = "projects/index.html"
    context_object_name = "projects_list"

    def get_queryset(self):
        result = []
        for user in User.objects.all().order_by('username'):
            projects = Project.objects.filter(user__exact=user)
            if self.request.user.pk != user.pk and not self.request.user.is_staff:
                projects = projects.filter(visible=True)
            if projects:
                result.append([user, projects])
        return result

class ProjectView(generic.DetailView):
    template_name = "projects/project.html"
    context_object_name = "project"

    def get_object(self):
        project = Project.objects.get(
            user__exact=User.objects.get(username__exact=self.kwargs["user"]),
            name__exact=self.kwargs["project"],
            git_branch__exact=self.kwargs["branch"]
        )

        # only public projects, or own project, or I am staff
        if not project.visible and not self.request.user.is_staff:
            if self.request.user != project.user:
                raise Exception("you do not have permission for this project")

        return project

def view_package(request, user, project, package):

    package = Package.objects.get(
        project__exact=Project.objects.get(
            user__exact=User.objects.get(username__exact=user),
            name__exact=project
        ),
        name__exact=package
    )

    # only public projects, or own project, or I am staff
    if not package.project.visible and not request.user.is_staff:
        if request.user != package.project.user:
            raise Exception("you do not have permission for this project")

    logger = Logger()
    builds_per_target_and_branch = logger.getBuildsOfPackage(package)
    lbs = LightBuildServer()
    (repoInstructions, srcInstructions, winInstructions) = lbs.GetAllInstructions(package)

    if package.project.git_type == 'github':
        project_browse_url = f"{package.project.git_url}/tree/{package.project.git_branch}"
    elif package.project.git_type == 'gitea':
        project_browse_url = f"{package.project.git_url}/src/branch/{package.project.git_branch}"
    elif package.project.git_type == 'gitlab':
        project_browse_url = f"{package.project.git_url}/-/tree/{package.project.git_branch}"

    template_name = "projects/package.html"
    return render(request, template_name,
            {
             'package': package,
             'project_browse_url': project_browse_url,
             'builds_per_target_and_branch': builds_per_target_and_branch,
             'repoinstructions_per_buildtarget': repoInstructions,
             'srcinstructions_per_buildtarget': srcInstructions,
             'wininstructions_per_branchname': winInstructions,
            })
