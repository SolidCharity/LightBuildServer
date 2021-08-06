from itertools import chain
from django.views import generic
from django.contrib.auth.models import User

from .models import Project

class IndexView(generic.ListView):
    template_name = "projects/index.html"
    context_object_name = "projects_list"

    def get_queryset(self):
        return [ (user, Project.objects.filter(user__exact=user)) for user in (
            chain([self.request.user], User.objects.exclude(pk__exact=self.request.user.pk))
                if self.request.user.is_authenticated else User.objects.all()
        ) ]
