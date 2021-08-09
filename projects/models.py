from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from machines.models import Machine


class Project(models.Model):
    name = models.CharField(max_length=250)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    git_url = models.CharField(max_length=250)
    git_branch = models.CharField(max_length=250)
    use_lxc = models.BooleanField()
    public_key = models.TextField(null=True, blank=True)  # generate keys autom. at project setup
    private_key = models.TextField(null=True, blank=True)
    machine = models.ForeignKey(Machine, on_delete=models.SET_NULL, null=True, blank=True)
    copr_user_name = models.CharField(max_length=250, null=True, blank=True)    # solve copr-stuff later
    copr_project_name = models.CharField(max_length=250, null=True, blank=True)
    use_docker = models.BooleanField()
    visible = models.BooleanField()

    def __str__(self):
        return self.name
    
    def get_buildtargets(self):
        return sorted(set([distro for package in self.package_set.all() for distro in package.distro_set.all()]))

    class Meta:
        ordering = ("name",)


class Package(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    machine = models.ForeignKey(Machine, on_delete=models.SET_NULL, null=True, blank=True)
    use_docker = models.BooleanField()
    windows_installer = models.BooleanField()

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ("name",)


class Distro(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ("name",)


class Branch(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "branches"
