# Generated by Django 2.2.8 on 2020-09-02 13:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("webservice", "0005_webservicevariable_path"),
    ]

    operations = [
        migrations.AlterField(
            model_name="webserviceaction",
            name="webservice_mode",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "Path"), (1, "GET"), (2, "POST")], default=0
            ),
        ),
    ]
