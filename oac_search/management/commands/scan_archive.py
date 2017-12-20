import tarfile
import datetime
from os.path import split, splitext, getctime
from os import stat
import platform
import pytz
from django.core.management.base import BaseCommand


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
    help = 'Scan archive and perform different checks'

    def add_arguments(self, parser):
        parser.add_argument('archive', help="Archive path")
        parser.add_argument('--check_names', action='store_true', help="check if names of files are valid")

    def handle(self, *args, **options):
        ifpath = options['archive']
        check_names = options['check_names']

        if check_names:
            self.check_names(ifpath)

    def check_names(self, archName):
        with tarfile.open(archName, 'r:gz') as tar:
            for i, tarinfo in enumerate(tar):
                if tarinfo.isreg():
                    ext = splitext(split(tarinfo.name)[1])[1].lower()
                    if ext not in ['.xml', '.nxml']:
                        print('archive "{}": not XML: "{}"'.format(archName, tarinfo.name))

                    pmcid = splitext(split(tarinfo.name)[1])[0]
                    if not pmcid.startswith('PMC') or len(pmcid) > 20:
                        print('archive "{}": invalid PMCID: "{}"'.format(archName, tarinfo.name))
