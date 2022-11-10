from django.db import models
from django.contrib.auth.models import User

class Build(models.Model):
    number = models.IntegerField(default=-1)
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
    designated_build_machine = models.CharField(max_length=250, default=None, null=True)
    avoidlxc = models.BooleanField(default = False)
    avoiddocker = models.BooleanField(default = False)
    dependsOnOtherProjects = models.TextField(default=None, null=True)
    started = models.DateTimeField(default=None, null=True)
    finished = models.DateTimeField(default=None, null=True)
    hanging = models.BooleanField(default=False)
    buildsuccess = models.CharField(max_length=20,default=None, null=True)


class Log(models.Model):
    build = models.ForeignKey(Build, on_delete=models.CASCADE)
    line = models.TextField()
    created = models.DateTimeField()
