import tarfile
import datetime
from os.path import split, splitext, getctime, join
from os import stat
import platform
import pytz
import time
from django.core.management.base import BaseCommand

# from oac_search import models, parse_xml


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
    help = 'Scan archive and perform different procedures'

    def add_arguments(self, parser):
        parser.add_argument('archive', help="Archive path")
        parser.add_argument('--check_names', action='store_true', help="check if names of files are valid")

    def handle(self, *args, **options):
        ifpath = options['archive']
        check_names = options['check_names']

        if check_names:
            self.check_names(ifpath)

    def check_names(self, archName):
        # onetime = True
        with tarfile.open(archName, 'r:gz') as tar:
            # processed = 0
            # errors = {'file': [], 'content': []}
            for i, tarinfo in enumerate(tar):
                # if i >= 50:
                #     break
                if tarinfo.isreg():
                    # print(tarinfo.name)
                    # fp = tar.extractfile(tarinfo)
                    ext = splitext(split(tarinfo.name)[1])[1].lower()
                    if ext not in ['.xml', '.nxml']:
                        print('archive "{}": not XML: "{}"'.format(archName, tarinfo.name))

                    pmcid = splitext(split(tarinfo.name)[1])[0]
                    if not pmcid.startswith('PMC') or len(pmcid) > 20:
                        print('archive "{}": invalid PMCID: "{}"'.format(archName, tarinfo.name))
                        # if onetime:
                        #     fp = tar.extractfile(tarinfo)
                        #     with open(join('/home/vid/programiranje/wingIDE_projects/pmcutils/', split(tarinfo.name)[1]), 'wb') as ofp:
                        #         ofp.write(fp.read())
                        #     onetime = False

                if (i+1) % 10000 == 0:
                    print('---> {} files processed'.format(i+1))
