from django.contrib import admin
from .models import Machine


class MachineAdmin(admin.ModelAdmin):
    list_display = ['host', 'type', 'enabled']

    class Meta:
        None


admin.site.register(Machine, MachineAdmin)
