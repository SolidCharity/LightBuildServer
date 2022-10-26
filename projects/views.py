from itertools import chain
from django.views import generic
from django.contrib.auth.models import User

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
        if project.visible == False:
            if not self.request.user.is_staff:
                if self.request.user != project.user:
                    raise Exception("you do not have permission for this project")

        return project

class PackageView(generic.DetailView):
    template_name = "projects/package.html"
    context_object_name = "package"

    def get_object(self):
        package = Package.objects.get(
            project__exact=Project.objects.get(
                user__exact=User.objects.get(username__exact=self.kwargs["user"]),
                name__exact=self.kwargs["project"]
            ),
            name__exact=self.kwargs["package"]
        )

        # only public projects, or own project, or I am staff
        if package.project.visible == False:
            if not self.request.user.is_staff:
                if self.request.user != package.project.user:
                    raise Exception("you do not have permission for this project")

        return package
