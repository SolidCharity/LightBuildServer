from django.views import generic

from .models import Machine

class IndexView(generic.ListView):
    template_name = "machines/index.html"
    context_object_name = "machines_list"

    def get_queryset(self):
        return Machine.objects.get_queryset() # show only user's machines
