from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Machine(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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

    def __str__(self):
        return self.host
    
    class Meta:
        ordering = ("host",)
