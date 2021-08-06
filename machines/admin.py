from django.contrib import admin

from .models import Machine


admin.site.register([
    Machine,
])
