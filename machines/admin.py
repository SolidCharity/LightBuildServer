from django.contrib import admin
from .models import Machine


class MachineAdmin(admin.ModelAdmin):
    list_display = ['host', 'type', 'enabled']
    fields = ['host', 'type', 'port', 'cid', 'enabled', 'priority', 'static', 'local', 'private_key']

    class Meta:
        None


admin.site.register(Machine, MachineAdmin)
