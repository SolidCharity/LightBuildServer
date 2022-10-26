from django.contrib import admin

from .models import Project, Package, Distro, Branch


class DistroAdminInline(admin.TabularInline):
    model = Distro


class PackageAdminInline(admin.TabularInline):
    model = Package
    fields = ('name', 'changeform_link')
    readonly_fields = ('changeform_link',)


class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'visible']
    inlines = (PackageAdminInline, )

    class Meta:
        None


class PackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'project']
    inlines = (DistroAdminInline, )

    class Meta:
        None


admin.site.register(Package, PackageAdmin)
admin.site.register(Project, ProjectAdmin)
