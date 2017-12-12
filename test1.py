import tarfile
from bs4 import BeautifulSoup as bs
from os.path import split, splitext

with tarfile.open('/home/vid/temp/PMCOAC/non_comm_use.A-B.xml.tar.gz', 'r:gz') as tar:
    for i, tarinfo in enumerate(tar):
        if i >= 1:
            break
        if tarinfo.isreg():
            # print(tarinfo.name)
            fp = tar.extractfile(tarinfo)
            ext = splitext(split(tarinfo.name)[1])[1].lower()
            if ext not in ['.xml', '.nxml']:
                continue
            else:
                xmldata = fp.read()
                print(xmldata)
