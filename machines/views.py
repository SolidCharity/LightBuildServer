from django.db.models import Q
from django.shortcuts import render, redirect

from .models import Machine
from builder.models import Build
from lib.LightBuildServer import LightBuildServer

def monitor(request, successmessage = None, errormessage = None):
    template_name = "machines/index.html"
    machines_list = Machine.objects.all()
    lbs = LightBuildServer()
    return render(request, template_name,
            {
             'successmessage': successmessage,
             'errormessage': errormessage,
             'machines_list': machines_list,
             'waiting_builds': lbs.GetBuildQueue(request.user),
             'finished_builds': lbs.GetFinishedQueue(request.user),
            })

def reset(request, machine_name):
    lbs = LightBuildServer()

    lbs.ReleaseMachine(machine_name, True)

    successmessage = f"The machine {machine_name} should now be available."
    return monitor(request, successmessage)