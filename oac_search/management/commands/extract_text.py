from django.core.management.base import BaseCommand

from oac_search import models, parse_xml as parser


class Command(BaseCommand):
    help = 'Exract text from articles in the database and store it'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help="force extract")

    def handle(self, *args, **options):
        force = options['force']
        articles = models.Article.objects.filter(text="") if not force else models.Article.objects.all()

        print('Starting extract process...')
        errors = []
        cnt = 0
        for i, a in enumerate(articles):
            try:
                fulltext = parser.extract_text(a.xml, skipTags=[])
                cnt += 1
            except:
                errors.append(a.pmcid)
            else:
                a.text = fulltext
                a.save()
            if (i+1)%100==0:
                print('{} articles processed'.format(i+1))

        if errors:
            print('{} not extracted due to parser errors'.format(len(errors)))
        print('Extract completed, {} articles processed'.format(cnt))
    # end
