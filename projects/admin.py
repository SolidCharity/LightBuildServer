from django.contrib import admin

from .models import Project, Package, Distro, Branch, ProjectFile


class DistroAdminInline(admin.TabularInline):
    model = Distro

class BranchAdminInline(admin.TabularInline):
    model = Branch


class PackageAdminInline(admin.TabularInline):
    model = Package
    fields = ('name', 'changeform_link')
    readonly_fields = ('changeform_link',)


class ProjectFileAdminInline(admin.TabularInline):
    model = ProjectFile
    fields = ('filename', 'changeform_link')
    readonly_fields = ('changeform_link',)


class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'visible']
    inlines = (PackageAdminInline, ProjectFileAdminInline)

    class Meta:
        None


class ProjectFileAdmin(admin.ModelAdmin):
    list_display = ['project', 'filename']


class PackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'project']
    inlines = (DistroAdminInline, BranchAdminInline, )

    class Meta:
        None


admin.site.register(Package, PackageAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(ProjectFile, ProjectFileAdmin)
