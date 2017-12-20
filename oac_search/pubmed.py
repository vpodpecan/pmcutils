import os
import argparse
import urllib.request, urllib.error, urllib.parse
from xml.etree import cElementTree as tree
import time
import codecs
import unidecode
from bs4 import BeautifulSoup as bs
import sys

try:
    from .api_key import API_KEY
except ImportError:
    print('API_KEY variable not present in api_key.py')
    API_KEY = None


def extract_text(xmldata, skipTags=['xref', 'table', 'graphic', 'ext-link',
                                    'media', 'inline-formula', 'disp-formula', 'references',
                                    'ref-list', 'ack', 'front', 'back', 'permissions', 'notes']):
    root = bs(xmldata, 'xml')
    for tag in skipTags:
        _ = [x.extract() for x in root.find_all(tag)]
        # unwanted = root.find_all(tag)
        # unwanted.extract()
    text = root.get_text(separator=u' ').strip().replace('\n', ' ').replace('\t', ' ').replace('  ', ' ').replace('  ', ' ')
    return text


def find_pmcid(xmldata):
    root = bs(xmldata, 'xml')
    aid = root.find('article-id', attrs={'pub-id-type': 'pmc'})
    if aid is not None:
        pmcid = aid.text.strip()
        if not pmcid.startswith('PMC'):
            pmcid = 'PMC' + pmcid
        return pmcid
    else:
        raise Exception('PMCID not found')


class NCBI_search:
    qwait = 5.0
    maxdoc = 100000

    searchURL = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
    fetchURL = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
    pmcURL = 'http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3315246/'

    def __init__(self):
        self.last_qdate = 0

    def dispatchRequest(self, q):
        td = time.time() - self.last_qdate
        if td < self.qwait:
            time.sleep(self.qwait - td)

        self.last_qdate = time.time()
        return urllib.request.urlopen(urllib.request.Request(q), timeout=60).read()

    def getIDs(self, queryURL, maxHits=0):
        ids = []
        cnt = 1

        # first batch of results
        result = self.dispatchRequest(queryURL)
        t = tree.fromstring(result)
        ids.extend([x.text for x in t.find('IdList').findall('Id')])
        hits = int(t.find('Count').text)
        sys.stdout.write('Total hits: {}\n'.format(hits))

        sys.stdout.write('batch: {}, got: {}\n'.format(cnt, len(ids)))
        # if we have enough already
        if maxHits > 0 and (len(ids) > maxHits or maxHits > hits):
            return ids[:maxHits]

        # if there are more, get them also with retstart option
        while len(ids) < hits:
            nq = queryURL + '&retstart=%d&retmax=%d' % (len(ids), self.maxdoc)
            result = self.dispatchRequest(nq)
            t = tree.fromstring(result)
            ids.extend([x.text for x in t.find('IdList').findall('Id')])
            cnt += 1
            sys.stdout.write('batch: {}, total: {}'.format(cnt, len(ids)))
            if maxHits and len(ids) >= maxHits:
                break
        if maxHits:
            return ids[:maxHits]
        else:
            return ids

    def query(self, queryText, db='pmc', maxHits=0, onlyFreetext=True, onlyOAC=True):
        if not queryText:
            raise ValueError('Empty query!')

        qtparam = ''
        if onlyFreetext:
            qtparam += ' AND free fulltext[filter]'
        if onlyOAC:
            qtparam += ' AND open access[filter]'

        query = [('api_key', NCBI_API_KEY_PODPECAN), ('db', db), ('term', queryText + qtparam)]

        query.append(('retmax', self.maxdoc))
        query = '%s?%s' % (self.searchURL, urllib.parse.urlencode(query))
        print(query)
        ids = self.getIDs(query, maxHits=maxHits)
        return ids


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--queryfile', required=True, help='input file with query text')
    parser.add_argument('-o', '--output', required=True, help='oputput file with PMC ids')
    parser.add_argument('-f', '--free', action='store_true', help='only free fulltext articles')
    parser.add_argument('-c', '--oac', action='store_true', help='only OAC articles')

    args = parser.parse_args()

    if not os.path.exists(args.queryfile):
        print('Error: query input file does not exist.')
        exit(1)

    qtext = unidecode.unidecode(codecs.open(args.queryfile, encoding='utf-8').read().strip())
    if not qtext:
        print('Error: empty query text.')
        exit(1)

    a = NCBI_search()
    free = args.free
    oac = args.oac
    pmcids = a.query(qtext, db='pmc', onlyFreetext=free, onlyOAC=oac)
    with open(args.output, 'w') as ofp:
        text = '\n'.join(['PMC' + x for x in pmcids])
        ofp.write(text)
