from django.contrib import admin

from .models import Project, Package, Distro, Branch


admin.site.register([
    Project,
    Package,
    Distro,
    Branch,
])
