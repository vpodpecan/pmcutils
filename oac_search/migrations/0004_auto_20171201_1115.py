# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-01 11:15
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oac_search', '0003_auto_20171201_1104'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='article',
            index_together=set([('pmcid',)]),
        ),
    ]
