from django.db import models
from django.contrib.auth.models import User

class Build(models.Model):
    status = models.CharField(max_length=20, choices=[
        ("WAITING", "waiting"),
        ("BUILDING", "building"),
        ("CANCELLED", "cancelled"),
        ("FINISHED", "finished"),
    ])
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    project = models.CharField(max_length=250)
    secret = models.BooleanField()
    package = models.CharField(max_length=250)
    branchname = models.CharField(max_length=250)
    distro = models.CharField(max_length=20)
    release = models.CharField(max_length=20)
    arch = models.CharField(max_length=10)
    # this is used for packages or projects that should run on a designated build machine.
    # we are not using a link to avoid circular dependencies
    designated_build_machine = models.CharField(max_length=250, default=None)
    avoidlxc = models.BooleanField()
    avoiddocker = models.BooleanField()
    dependsOnOtherProjects = models.TextField(default=None)
    started = models.DateTimeField(default=None)
    finished = models.DateTimeField(default=None)
    hanging = models.BooleanField(default=False)
    buildsuccess = models.CharField(max_length=20,default=None)


class Log(models.Model):
    build = models.ForeignKey(Build, on_delete=models.CASCADE, default=None)
    line = models.TextField()
    created = models.DateTimeField()
