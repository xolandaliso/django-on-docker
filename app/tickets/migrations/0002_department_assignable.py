# Generated by Django 4.2.13 on 2024-07-29 11:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='department',
            name='assignable',
            field=models.BooleanField(default=False),
        ),
    ]