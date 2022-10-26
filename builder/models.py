from django.db import models
from projects.models import Package, Project, Distro
from machines.models import Machine

class Build(models.Model):
    status = models.CharField(max_length=20, choices=[
        ("WAITING", "waiting"),
        ("BUILDING", "building"),
        ("CANCELLED", "cancelled"),
        ("FINISHED", "finished"),
    ])
    user = max_length=250
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    secret = models.BooleanField()
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    branchname = models.CharField(max_length=250)
    distro = models.ForeignKey(Distro, on_delete=models.CASCADE)
    release = models.CharField(max_length=20)
    arch = models.CharField(max_length=10)
    avoidlxc = models.BooleanField()
    avoiddocker = models.BooleanField()
    dependsOnOtherProjects = models.TextField()
    buildmachine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    started = models.DateTimeField()
    finished = models.DateTimeField()
    hanging = models.BooleanField()
    buildsuccess = models.CharField(max_length=20)
    buildnumber = models.IntegerField()

    def __str__(self):
        return self.buildnumber
    
    class Meta:
        ordering = ("buildnumber",)
