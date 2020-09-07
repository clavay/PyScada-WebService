# Generated by Django 2.2.8 on 2020-09-07 09:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pyscada', '0059_auto_20200211_1049'),
        ('webservice', '0009_auto_20200904_1042'),
    ]

    operations = [
        migrations.AddField(
            model_name='webserviceaction',
            name='webservice_RW',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Read'), (1, 'Write')], default=0),
        ),
        migrations.AddField(
            model_name='webserviceaction',
            name='write_trigger',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='write_trigger', to='pyscada.Variable'),
        ),
        migrations.AlterField(
            model_name='webserviceaction',
            name='path',
            field=models.CharField(blank=True, help_text='look at the readme', max_length=400, null=True),
        ),
        migrations.AlterField(
            model_name='webserviceaction',
            name='variables',
            field=models.ManyToManyField(related_name='variables', to='pyscada.Variable'),
        ),
        migrations.AlterField(
            model_name='webservicevariable',
            name='path',
            field=models.CharField(blank=True, help_text='look at the readme', max_length=254, null=True),
        ),
    ]
