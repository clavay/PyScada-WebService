# Generated by Django 2.2.8 on 2020-12-09 11:33

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("webservice", "0015_auto_20201209_1133"),
    ]

    operations = [
        migrations.RenameField(
            model_name="webservicedevice",
            old_name="ip_or_dns",
            new_name="url",
        ),
    ]
