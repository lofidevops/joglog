# Generated by Django 3.0.6 on 2020-05-27 12:40

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('jogging', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='joggingsession',
            name='distance',
            field=models.IntegerField(default=0, verbose_name='distance (meters)'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='joggingsession',
            name='dn_speed',
            field=models.DecimalField(decimal_places=1, default=0, editable=False, max_digits=3, verbose_name='calculated speed (km/h)'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='joggingsession',
            name='dn_week',
            field=models.DecimalField(decimal_places=2, default=2020.0, editable=False, max_digits=6, verbose_name='calculated calendar week (YYYY.WW)'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='joggingsession',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='joggingsession',
            name='is_in_report',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='joggingsession',
            name='local_timezone',
            field=models.TextField(blank=True, verbose_name='local timezone (tzdb)'),
        ),
        migrations.AddField(
            model_name='joggingsession',
            name='start',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='start time (UTC)'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='joggingsession',
            name='user',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='joggingsession',
            name='duration',
            field=models.IntegerField(verbose_name='duration (minutes)'),
        ),
    ]
