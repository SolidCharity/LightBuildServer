from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

from builder.models import Build

class Machine(models.Model):
    host = models.CharField(max_length=250)
    port = models.PositiveIntegerField(validators=[ # not validators -> min_value, max_value
        MinValueValidator(0),
        MaxValueValidator(65535),
    ])
    type = models.CharField(max_length=20, choices=[
        ("lxd", "LXD"),
        ("docker", "Docker"),
        ("copr", "Copr"),
    ])
    private_key = models.TextField()
    static = models.BooleanField()
    local = models.BooleanField()
    priority = models.IntegerField()
    cid = models.IntegerField()
    enabled = models.BooleanField()

    status = models.CharField(max_length=20, default="AVAILABLE", choices=[
        ("AVAILABLE", "AVAILABLE"),
        ("BUILDING", "BUILDING"),
        ("STOPPING", "STOPPING"),
    ])

    # link to the current build running on this machine
    build = models.ForeignKey(Build, on_delete=models.PROTECT, default=None, null=True)

    def __str__(self):
        return self.host

    class Meta:
        ordering = ("host",)

        constraints = [
            models.UniqueConstraint(fields=["host"],name="unique_host")
        ]
