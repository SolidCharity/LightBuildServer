# Generated by Django 3.2.6 on 2021-08-09 17:18

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Machine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('host', models.CharField(max_length=250)),
                ('port', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(65535)])),
                ('type', models.CharField(choices=[('lxd', 'LXD'), ('docker', 'Docker'), ('copr', 'Copr')], max_length=20)),
                ('private_key', models.TextField()),
                ('static', models.BooleanField()),
                ('local', models.BooleanField()),
                ('priority', models.IntegerField()),
                ('cid', models.IntegerField()),
                ('enabled', models.BooleanField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('host',),
            },
        ),
    ]
