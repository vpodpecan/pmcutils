import os
import logging
import gzip

from django.core.management.base import BaseCommand

from oac_search import models, pubmed

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)


class Command(BaseCommand):
    help = 'Search and export full text OAC articles from the database (no on-the-fly XML extraction!)'

    def add_arguments(self, parser):
        parser.add_argument('queryfile', help="query file")

    def handle(self, *args, **options):
        # clean = options['clean']
        # full = options['full']
        queryfile = options['queryfile']
        path = os.path.abspath(queryfile)
        query = open(queryfile).read().replace('\n', ' ').strip()

        idfile = os.path.join(path, queryfile + '.pmcids')
        fullfile = os.path.join(path, queryfile + '.fulltext.gz')

        a = pubmed.NCBI_search()
        pmcids = a.query(query, db='pmc', onlyOAC=True)
        pmcids = ['PMC' + x for x in pmcids]
        with open(idfile, 'w') as ofp:
            ofp.write('\n'.join(pmcids))

        logging.info('Total PMC IDs: {}; present in DB: {}'.format(len(pmcids), models.Article.objects.filter(pmcid__in=pmcids).count()))
        with gzip.open(fullfile, 'wt') as ofp:
            for article in models.Article.objects.filter(pmcid__in=pmcids).iterator():
                ofp.write('{}\t{}\n'.format(article.pmcid, article.text))
        logging.info('Export complete.')
