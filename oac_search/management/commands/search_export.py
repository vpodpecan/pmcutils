import os
import logging
import gzip
import json
from psycopg2 import sql
from undecorated import undecorated

from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
from django.http import HttpRequest

from oac_search import models, pubmed, views

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
# settings.configure()


class FakeRequest(HttpRequest):
    method = 'POST'
    limited = False

    def __init__(self):
        super().__init__()


class Command(BaseCommand):
    help = 'Search and export articles just like in the web interface.'

    def add_arguments(self, parser):
        parser.add_argument('query_parameters', help="a config file with parameters in JSON format")

    def handle(self, *args, **options):
        with open(options['query_parameters']) as fp:
            params = json.load(fp)

        request = HttpRequest()
        request.method = 'POST'
        request.limited = False
        request.POST['SERVER_NAME'] = 'localhost'
        request.POST['q'] = params['query']
        request.POST['t'] = params['tags']
        request.POST['it'] = params['ignored_tags']
        request.POST['ss'] = params['sample_size']
        request.POST['n'] = params['return_only_nonempty']
        request.POST['st'] = params['PMC_subset']
        request.POST['cl'] = params['doc_class_label']

        api_function = undecorated(views.api)
        result = json.loads(api_function(request).content.decode())  # get back the data from bytes dumped content
        for key in result:
            print('{}: {}'.format(key, result[key]))
        logging.info('Export complete.')
