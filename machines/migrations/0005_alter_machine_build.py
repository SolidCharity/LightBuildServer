# Generated by Django 4.1.2 on 2022-11-05 14:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('builder', '0005_alter_build_avoiddocker_alter_build_avoidlxc'),
        ('machines', '0004_alter_machine_enabled_alter_machine_local_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='machine',
            name='build',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to='builder.build'),
        ),
    ]
