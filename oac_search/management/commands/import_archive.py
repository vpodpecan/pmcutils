import tarfile
import datetime
from os.path import split, splitext, getctime
from os import stat
import platform
import pytz
import time
from django.core.management.base import BaseCommand

from oac_search import models, pubmed


def get_creation_date(fpath):
    if platform.system() == 'Windows':
        return datetime.datetime.fromtimestamp(getctime(fpath), pytz.utc)
    else:
        fstats = stat(fpath)
        try:
            return datetime.datetime.fromtimestamp(fstats.st_birthtime, pytz.utc)
        except AttributeError:
            return datetime.datetime.fromtimestamp(fstats.st_mtime, pytz.utc)


class Command(BaseCommand):
    help = 'Import all article files from an PMC OAC archive'

    def add_arguments(self, parser):
        parser.add_argument('archive', help="Archive path")
        parser.add_argument('--force', action='store_true', help="force import of an (older) archive")
        parser.add_argument('--extract', action='store_true', help="extract text on import")
        parser.add_argument('--overwrite', action='store_true', help='overwrite already imported articles')

    def handle(self, *args, **options):
        ifpath = options['archive']
        force = options['force']
        overwrite = options['overwrite']
        extractText = options['extract']
        ifdate = get_creation_date(ifpath)
        ifname = split(ifpath)[1]

        existing = models.Archive.objects.filter(name=ifname)
        if existing:
            newest = max(existing, key=lambda x: x.date)
            # print(newest.date, ifdate)
            if newest.date >= ifdate and not force:
                narticles = models.Article.objects.filter(archive=newest).count()
                print('A newer version of archive {} dated {} is already imported ({} articles).\nAborting import.\nHint: use the --force flag.'.format(ifname, ifdate, narticles))
                return

        arch, created = models.Archive.objects.get_or_create(name=ifname, date=ifdate)
        arch.save()

        print('Reading archive...')
        with tarfile.open(ifpath, 'r:gz') as tar:
            processed = 0
            skipped = 0
            errors = {'file': [], 'content': []}
            startTime = time.time()
            for i, tarinfo in enumerate(tar):
                if tarinfo.isreg():
                    fp = tar.extractfile(tarinfo)
                    ext = splitext(split(tarinfo.name)[1])[1].lower()
                    if ext not in ['.xml', '.nxml']:
                        errors['file'].append(tarinfo.name)
                        continue
                    else:
                        try:
                            xmldata = fp.read().decode('utf-8')
                        except Exception as e:
                            errors['content'].append(tarinfo.name)
                            print(e)
                            continue

                    # PMC is either the filename or it can be found inside xml
                    try:
                        pmcid = splitext(split(tarinfo.name)[1])[0]
                        if not pmcid.startswith('PMC'):
                            pmcid = pubmed.find_pmcid(xmldata)
                    except:
                        errors['file'].append(tarinfo.name)
                        continue

                    (new, created) = models.Article.objects.get_or_create(pmcid=pmcid)
                    if not created and not overwrite:
                        skipped += 1
                        if (i+1) % 100 == 0:
                            print('{} articles processed'.format(i+1))
                        continue
                    new.path = tarinfo.name
                    new.archive = arch
                    new.xml = xmldata
                    if extractText:
                        try:
                            new.text = pubmed.extract_text(xmldata, skipTags=[])
                            new.cleantext = pubmed.extract_text(xmldata)
                        except:
                            errors['content'].append(tarinfo.name)
                            continue
                    else:
                        new.text = ''
                        new.cleantext = ''
                    new.save()

                    processed += 1
                    if (i+1) % 100 == 0:
                        print('{} articles processed'.format(i+1))
        endTime = time.time()
        print()
        if errors['file']:
            print('{} not imported due to errors'.format(len(errors)))
        if errors['content']:
            print('{} not extracted due to errors'.format(len(errors)))
        print('{} article(s) imported'.format(processed))
        if skipped:
            print('{} skipped (use --overwrite to import again)'.format(skipped))
        speed = processed / (endTime-startTime)
        print('Time: {:.0f} second(s), average speed: {:.1f} article/second'.format(endTime-startTime, speed))
