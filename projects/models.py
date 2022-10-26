from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from machines.models import Machine


class Project(models.Model):
    name = models.CharField(max_length=250)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    git_url = models.CharField(max_length=250)
    git_branch = models.CharField(max_length=250)
    public_key = models.TextField(null=True, blank=True)  # generate keys autom. at project setup
    private_key = models.TextField(null=True, blank=True)
    machine = models.ForeignKey(Machine, on_delete=models.SET_NULL, null=True, blank=True)
    copr_user_name = models.CharField(max_length=250, null=True, blank=True)    # solve copr-stuff later
    copr_project_name = models.CharField(max_length=250, null=True, blank=True)
    use_lxc = models.BooleanField(default = False)
    use_docker = models.BooleanField(default = False)
    visible = models.BooleanField(default = True)

    def __str__(self):
        return f"{self.user}::{self.name}"

    def get_buildtargets(self):
        targets = []
        for package in self.package_set.all():
            for distro in package.distro_set.all():
                targets.append(distro.name.replace("/", "__"))
        return sorted(targets)

    class Meta:
        ordering = ("name",)


class Package(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    machine = models.ForeignKey(Machine, on_delete=models.SET_NULL, null=True, blank=True)
    use_docker = models.BooleanField(default = False)
    windows_installer = models.BooleanField(default = False)

    def __str__(self):
        return self.name

    def changeform_link(self):
        if self.id:
            changeform_url = reverse(
                'admin:projects_package_change', args=(self.id,)
            )
            return mark_safe(f'<a href="{changeform_url}" target="_blank">Details</a>')
        return u''
    changeform_link.allow_tags = True
    changeform_link.short_description = ''   # omit column header

    def get_buildtargets(self):
        targets = []
        for distro in self.distro_set.all():
            targets.append(distro.name.replace("/", "__"))
        return sorted(targets)

    def get_branches(self):
        branches = []
        for branch in self.branch_set.all():
            branches.append(branch.name)
        if not branches:
            branches.append(self.project.git_branch)
        return sorted(branches)

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