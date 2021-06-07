import os
import logging
import gzip

from psycopg2 import sql

from django.core.management.base import BaseCommand
from django.db import connection

from oac_search import models, pubmed

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)


class Command(BaseCommand):
    help = 'Search and export full text OAC articles from the database (no on-the-fly XML extraction!)'

    def add_arguments(self, parser):
        parser.add_argument('queryfile', help="query file")

    def handle(self, *args, **options):
        queryfile = options['queryfile']
        path = os.path.split(os.path.abspath(queryfile))[0]
        query = open(queryfile).read().replace('\n', ' ').strip()

        idfile = os.path.join(path, queryfile + '.pmcids')
        fullfile = os.path.join(path, queryfile + '.fulltext.gz')

        a = pubmed.NCBI_search()
        pmcids = a.query(query, db='pmc', onlyOAC=True)
        pmcids = ['PMC' + x for x in pmcids]
        with open(idfile, 'w') as ofp:
            ofp.write('\n'.join(pmcids))

        logging.info('Total PMC IDs: {}; present in DB: {}'.format(len(pmcids), models.Article.objects.filter(pmcid__in=pmcids).count()))
        with gzip.open(fullfile, 'wt', encoding='utf8') as ofp:

            with connection.cursor() as cursor:
                cursor.execute('''DROP TABLE IF EXISTS _result_pmcids_''')
                cursor.execute('''CREATE TABLE _result_pmcids_ (
                                        id serial primary key,
                                        pmcid varchar(20) unique not null)''')
                connection.commit()
                with open(idfile) as fp:
                    cursor.copy_from(fp, '_result_pmcids_', columns=('pmcid',))
                connection.commit()
                cursor.execute('''SELECT oac_search_article.pmcid, oac_search_article.text
                                  FROM oac_search_article
                                  INNER JOIN _result_pmcids_ ON oac_search_article.pmcid = _result_pmcids_.pmcid''')
                for pmcid, text in cursor:
                    ofp.write('{}\t{}\n'.format(pmcid, text))
                cursor.execute('''DROP TABLE IF EXISTS _result_pmcids_''')
        logging.info('Export complete.')
