from itertools import chain
from django.views import generic
from django.contrib.auth.models import User

from .models import Project, Package


class IndexView(generic.ListView):
    template_name = "projects/index.html"
    context_object_name = "projects_list"

    def get_queryset(self):
        return [ (user, Project.objects.filter(user__exact=user)) for user in (
            chain([self.request.user], User.objects.exclude(pk__exact=self.request.user.pk))
                if self.request.user.is_authenticated else User.objects.all()
        ) ]

class ProjectView(generic.DetailView):
    template_name = "projects/project.html"
    context_object_name = "project"

    def get_object(self):
        return Project.objects.get(
            user__exact=User.objects.get(username__exact=self.kwargs["user"]),
            name__exact=self.kwargs["project"],
            git_branch__exact=self.kwargs["branch"]
        )

class PackageView(generic.DetailView):
    template_name = "projects/package.html"
    context_object_name = "package"

    def get_object(self):
        return Package.objects.get(
            project__exact=Project.objects.get(
                user__exact=User.objects.get(username__exact=self.kwargs["user"]),
                name__exact=self.kwargs["project"],
                git_branch__exact=self.kwargs["branch"]
            ),
            name__exact=self.kwargs["package"]
        )
