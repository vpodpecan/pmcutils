import sys
import urllib.request, urllib.error, urllib.parse
import urllib.request, urllib.parse, urllib.error
import os
from xml.etree import cElementTree as tree
import time
import re
import xml.dom.minidom as dom
import codecs
import unidecode
import argparse
import traceback
import pickle


NCBI_API_KEY_PODPECAN = '21b0ad51c2c17037424700195e7fc5e14608'

class Document(object):
    def __init__(self):
        self.docid = None
        self.year = None
        self.title = None
        self.abstract = None
        self.body = None
        #self.text = None
        self.xml = None
    #end

    def write_content_text(self, outdir, utf=True):
        assert(os.path.isdir(outdir))
        if utf:
            fp = codecs.open(os.path.join(outdir, self.docid + '.txt'), 'w', encoding='utf-8')
            fp.write(self.title + '\n' + self.abstract + '\n' + self.body)
        else:
            fp = open(os.path.join(outdir, self.docid + '.txt'), 'w')
            fp.write(unidecode.unidecode(self.title) + '\n' + unidecode.unidecode(self.abstract) + '\n' + unidecode.unidecode(self.body))
        fp.close()
#end


class NCBI_Extractor(object):
    #qwait = 0.33
    qwait = 5.0
    maxdoc = 100000

    searchURL = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
    fetchURL = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
    pmcURL = 'http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3315246/'

    def __init__(self):
        self.last_qdate = 0
    #end

    def dispatchRequest(self, q):
        # obey NCBI limitations (3 requests per second)
        td = time.time() - self.last_qdate
        if td < self.qwait:
            #print 'sleeping for %.2f seconds' % (self.qwait - td)
            time.sleep(self.qwait - td)

        self.last_qdate = time.time()
        return urllib.request.urlopen(urllib.request.Request(q), timeout=60).read()
    #end

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
        #end
        if maxHits:
            return ids[:maxHits]
        else:
            return ids
    #end

    def query(self, queryText, db='pmc', maxHits=0, onlyFreetext=True, onlyOAC=True):
        if not queryText:
            raise ValueError('Empty query!')

        qtparam = ''
        if onlyFreetext:
            qtparam += ' AND free fulltext[filter]'
        if onlyOAC:
            qtparam += ' AND open access[filter]'

        query = [('api_key', NCBI_API_KEY_PODPECAN), ('db', db), ('term', queryText + qtparam)]

        # if onlyOAC:
        #     query = [('db', db), ('term', queryText + ' AND free fulltext[filter]')]  # AND open access[filter]')]
        # else:
        #     query = [('db', db), ('term', queryText)]

        query.append(('retmax', self.maxdoc))
        print(query)
        query = '%s?%s' % (self.searchURL, urllib.parse.urlencode(query))
        print(query)
        ids = self.getIDs(query, maxHits=maxHits)
        return ids

    #end

#    def queryNEW(self, queryText, db='pmc', maxHits=0, onlyFulltext=True):
#        if not queryText:
#            raise ValueError('Empty query!')
#
#        if onlyFulltext:
#            payload = {'db': db, 'term': queryText + ' AND free fulltext[filter]'}
#        else:
#            payload = {'db': db, 'term': queryText}
#        payload['retmax'] = self.maxdoc
#
#        r = requests.get(self.searchURL, payload)
#        print r.url
#        return []
#        ids = self.getIDs(query, maxHits=maxHits)
#        return ids
#    # end


    def getDocument(self, did, db='pmc'):
        xml = self.getXML(did, db)
        root = dom.parseString(xml)
        doc = self.extractArticleText(root, did)
        doc.docid = did
        doc.xml = xml
        return doc
    #end

    def getDocumentBS4(self, did, db='pmc'):
        from bs4 import BeautifulSoup
        xml = self.getXML(did, db)
        root = BeautifulSoup(xml, 'lxml')
        alltext = root.get_text()
        return unidecode.unidecode(alltext)


    def getXML(self, did, db='pmc'):
        query = [('db', db), ('id', did)]
        url = '%s?%s' % (self.fetchURL, urllib.parse.urlencode(query))
        xml = self.dispatchRequest(url)
        return xml
    #end

    def getFulltext(self, did):
        xml = self.getXML(did)
        root = dom.parseString(xml)
        doc = self.extractArticleText(root, did)
        return doc

    def getDocumentFromXMLfile(self, fname, did=None):
        if not did:
            did = os.path.splitext(os.path.split(fname)[1])[0]
        #xml = open(fname).read()
        xml = codecs.open(fname, encoding='utf-8').read()
        #root = dom.parseString(xml)
        root = dom.parse(fname)
        doc = self.extractArticleText(root, did)
        doc.docid = did
        doc.xml = xml
        return doc
    #end

    def extractArticleText(self, root, did):
        try:
            titleNode = root.getElementsByTagName('article-title')[0]
        except Exception:
            title = ''
            print('Warning: no title found, document %s' % str(did))
        else:
            title = self.list2text(self.recursiveCollect(titleNode, []))

        try:
            abstractNode = root.getElementsByTagName('abstract')[0]
        except Exception:
            abstract = ''
            # print 'Warning: no abstract found, document %s' % str(did)
        else:
            abstract = self.list2text(self.recursiveCollect(abstractNode, []))
            abstract = re.sub('(\[)[ ,-:;]*(\])', '', abstract) # remove what remains of citations

        try:
            bodyNode = root.getElementsByTagName('body')[0]
        except Exception:
            body = ''
            #print 'Warning: no body found, document %s' % str(did)
        else:
            body = self.list2text(self.recursiveCollect(bodyNode, []))
            body = re.sub('(\[)[ ,-:;]*(\])', '', body)

        ytags = root.getElementsByTagName('pub-date')
        years = []
        for x in ytags:
            y = x.getElementsByTagName('year')
            if y:
                years.append(int(y[0].childNodes[0].data))
        year = min(years)

        new = Document()
        new.year = year
        new.title = title
        new.abstract = abstract
        new.body = body
        #new.text = abstract + ' ' + body
        return new
    #end


    def recursiveCollect(self, node, result, skipTags=['title', 'xref', 'table', 'graphic', 'ext-link',
                                                       'media', 'inline-formula', 'disp-formula']):
        for child in node.childNodes:
            if child.nodeType == dom.Node.ELEMENT_NODE:
                if child.tagName not in skipTags:
                    self.recursiveCollect(child, result)
            elif child.nodeType == dom.Node.TEXT_NODE:
                result.append(child.data)
        return result
    #end


    def list2text(self, lst):
        result = ''
        for x in lst:
            result += x.strip() + ' '
        return result.strip()
    #end
#end


########################################
### ALL LEUKEMIA SEARCH
#a = NCBI_Extractor()
##d = a.getDocument(2792210)
#ids = a.query('("t-lymphocytes"[MeSH Terms] OR "t-lymphocytes"[All Fields] OR "t cell"[All Fields] OR "t-cell"[All Fields]) OR ("leukaemia"[All Fields] OR "leukemia"[MeSH Terms] OR "leukemia"[All Fields])',
#              maxHits=1001)

#ids = a.query('leukemia', maxHits=10)
#fp = open('ALL-ids.pickle', 'wb')
#cPickle.dump(ids, fp, cPickle.HIGHEST_PROTOCOL)
#fp.close()
########################################


def extract_xml_from_folder(indir, outdir, utf):
    a = NCBI_Extractor()

    errs = []
    ok = []
    files = os.listdir(indir)
    sys.stderr.write('\n')
    for fname in files:
        fullName = os.path.join(indir, fname)
        if not os.path.isfile(fullName):
            continue
        sys.stderr.write('---> processing file %s ...  ' % (('"%s"' % fname).ljust(20)))
        try:
            doc = a.getDocumentFromXMLfile(fullName)
            doc.write_content_text(outdir, utf=utf)
        except Exception as e:
            errs.append(fname)
            sys.stderr.write('ERROR: "%s"\n' % str(e))
        else:
            ok.append(fname)
            sys.stderr.write('OK!\n')
    return ok, errs
#end


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

    a = NCBI_Extractor()
    free = args.free
    oac = args.oac
    pmcids = a.query(qtext, db='pmc', onlyFreetext=free, onlyOAC=oac)
    with open(args.output, 'w') as ofp:
        text = '\n'.join(['PMC' + x for x in pmcids])
        ofp.write(text)
