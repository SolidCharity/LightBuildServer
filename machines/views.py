from django.db.models import Q
from django.shortcuts import render, redirect

from .models import Machine
from builder.models import Build
from lib.LightBuildServer import LightBuildServer

def monitor(request):
    template_name = "machines/index.html"
    machines_list = Machine.objects.all()
    lbs = LightBuildServer()
    return render(request, template_name,
            {'machines_list': machines_list,
             'waiting_builds': lbs.GetBuildQueue(request.user),
             'finished_builds': lbs.GetFinishedQueue(request.user),
            })
