import tempfile
import zipfile
import os
import unidecode
from multiprocessing import Process, Queue
import psutil
from time import time, sleep
from datetime import datetime
# import shlex, subprocess
from random import sample

from bs4 import BeautifulSoup as bs
from ratelimit.decorators import ratelimit

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.conf import settings

from oac_search.forms import PUBTYPES, SearchForm
from oac_search import pubmed
from oac_search.models import Archive, Article


SENTINEL = 'STOP'


def _error(message):
    return JsonResponse({'status': False, 'message': message})


def _get_article_text(xmltags, article):
    tags = xmltags[0]
    ignoretags = xmltags[1]

    root = bs(article.xml, 'xml')
    for tag in ignoretags:
        if '=' in tag:
            parts = [x.strip() for x in tag.split('=')]
            if len(parts) != 2:
                continue
            atrval = eval(parts[1])
            tag_atr = [x.strip() for x in parts[0].split()]
            if len(tag_atr) != 2:
                continue
            blocktag = tag_atr[0]
            atrname = tag_atr[1]
            _ = [x.extract() for x in root.find_all(blocktag, attrs={atrname: eval(atrval)})]
        else:
            _ = [x.extract() for x in root.find_all(tag)]

    if not tags:
        text = root.get_text(separator=u' ')
    else:
        textblocks = []
        for tag in tags:
            if '=' in tag:
                parts = [x.strip() for x in tag.split('=')]
                if len(parts) != 2:
                    continue
                atrval = eval(parts[1])
                tag_atr = [x.strip() for x in parts[0].split()]
                if len(tag_atr) != 2:
                    continue
                blocktag = tag_atr[0]
                atrname = tag_atr[1]
                data = [x.get_text(separator=u' ') for x in root.find_all(blocktag, attrs={atrname: atrval})]
            else:
                data = [x.get_text(separator=u' ') for x in root.find_all(tag)]
            textblocks.extend(data)
        text = ' '.join(textblocks).strip()

    # replace all unicode line terminators
    for nl in ['\u000A', '\u000B', '\u000C', '\u000D', '\u0085', '\u2028', '\u2029']:
        text = text.replace(nl, ' ')
    text = text.replace('\t', ' ').strip()
    return article.pmcid, unidecode.unidecode(text)


def _get_article_text_fast(xmltags, article):
    tags = xmltags[0]
    ignoretags = xmltags[1]

    root = bs(article['xml'], 'xml')
    for tag in ignoretags:
        if '=' in tag:
            parts = [x.strip() for x in tag.split('=')]
            if len(parts) != 2:
                continue
            atrval = eval(parts[1])
            tag_atr = [x.strip() for x in parts[0].split()]
            if len(tag_atr) != 2:
                continue
            blocktag = tag_atr[0]
            atrname = tag_atr[1]
            _ = [x.extract() for x in root.find_all(blocktag, attrs={atrname: eval(atrval)})]
        else:
            _ = [x.extract() for x in root.find_all(tag)]

    if not tags:
        text = root.get_text(separator=u' ')
    else:
        textblocks = []
        for tag in tags:
            if '=' in tag:
                parts = [x.strip() for x in tag.split('=')]
                if len(parts) != 2:
                    continue
                atrval = eval(parts[1])
                tag_atr = [x.strip() for x in parts[0].split()]
                if len(tag_atr) != 2:
                    continue
                blocktag = tag_atr[0]
                atrname = tag_atr[1]
                data = [x.get_text(separator=u' ') for x in root.find_all(blocktag, attrs={atrname: atrval})]
            else:
                data = [x.get_text(separator=u' ') for x in root.find_all(tag)]
            textblocks.extend(data)
        text = ' '.join(textblocks).strip()

    # replace all unicode line terminators
    for nl in ['\u000A', '\u000B', '\u000C', '\u000D', '\u0085', '\u2028', '\u2029']:
        text = text.replace(nl, ' ')
    text = text.replace('\t', ' ').strip()
    return article['pmcid'], unidecode.unidecode(text)


class TextExtractor(Process):
    def __init__(self, tags, ignoretags, nonempty, docclass, group=None, target=None, name=None, args=(), kwargs={}):
        super(TextExtractor, self).__init__(group, target, name, args, kwargs)
        self.tags = tags
        self.ignoretags = ignoretags
        self.workQueue = Queue()
        # self.stopQueue = Queue()
        self.variables = Queue()
        self.nempty = 0
        self.nwritten = 0
        self.nonempty = nonempty
        self.docclass = docclass
        fid, self.tempfile = tempfile.mkstemp()
    # end

    def __del__(self):
        try:
            os.remove(self.tempfile)
        except:
            pass

    def __extract_text(self, xml):
        root = bs(xml, 'xml')
        for tag in self.ignoretags:
            if '=' in tag:
                parts = [x.strip() for x in tag.split('=')]
                if len(parts) != 2:
                    continue
                atrval = eval(parts[1])
                tag_atr = [x.strip() for x in parts[0].split()]
                if len(tag_atr) != 2:
                    continue
                blocktag = tag_atr[0]
                atrname = tag_atr[1]
                _ = [x.extract() for x in root.find_all(blocktag, attrs={atrname: eval(atrval)})]
            else:
                _ = [x.extract() for x in root.find_all(tag)]

        if not self.tags:
            text = root.get_text(separator=u' ')
        else:
            textblocks = []
            for tag in self.tags:
                if '=' in tag:
                    parts = [x.strip() for x in tag.split('=')]
                    if len(parts) != 2:
                        continue
                    atrval = eval(parts[1])
                    tag_atr = [x.strip() for x in parts[0].split()]
                    if len(tag_atr) != 2:
                        continue
                    blocktag = tag_atr[0]
                    atrname = tag_atr[1]
                    data = [x.get_text(separator=u' ') for x in root.find_all(blocktag, attrs={atrname: atrval})]
                else:
                    data = [x.get_text(separator=u' ') for x in root.find_all(tag)]
                textblocks.extend(data)
            text = ' '.join(textblocks).strip()

        # replace all unicode line terminators
        for nl in ['\u000A', '\u000B', '\u000C', '\u000D', '\u0085', '\u2028', '\u2029']:
            text = text.replace(nl, ' ')
        text = text.replace('\t', ' ').strip()
        return unidecode.unidecode(text)

    def run(self):
        for workload in iter(self.workQueue.get, SENTINEL):
            with open(self.tempfile, 'a') as fp:
                for pmcid, xml in workload:
                    try:
                        text = self.__extract_text(xml)
                    except:
                        text = ''
                    if text == '':
                        self.nempty += 1
                        if self.nonempty:
                            continue
                    if self.docclass:
                        line = '{} !{} {}\n'.format(pmcid, self.docclass, text)
                    else:
                        line = '{} {}\n'.format(pmcid, text)
                    fp.write(line)
                    self.nwritten += 1
        self.variables.put({'nempty': self.nempty, 'nwritten': self.nwritten, 'fname': self.tempfile})

# end


def index(request):
    context = {'form': SearchForm(initial={'pubtype': PUBTYPES[1][0]}),
               'archives': Archive.objects.all().order_by('name'),
               'narticles': Article.objects.count()}
    return render(request, 'oac_search/index.html', context)


@ratelimit(key='ip', method=ratelimit.ALL, rate='1/10s')
@ratelimit(key='ip', method=ratelimit.ALL, rate='5/m')
@ratelimit(key='ip', method=ratelimit.ALL, rate='30/h')
@ratelimit(key='ip', method=ratelimit.ALL, rate='200/d')
def api_query(request):
    was_limited = getattr(request, 'limited', False)
    if was_limited:
        return _error('Request blocked due to rate limiting. The rates are: 1 per 10 seconds, 5 per minute, 30 per hour, 200 per day')

    if request.method != 'POST':
        return _error('Invalid request')

    d = request.POST
    query = d.get('q', '')
    pubtype = d.get('st', '')
    if pubtype == 'free':
        onlyFreetext = True
        onlyOAC = False
    elif pubtype == 'oac':
        onlyFreetext = False
        onlyOAC = True

    if not query or not pubtype or pubtype not in [x[0] for x in PUBTYPES]:
        return _error('Invalid request')

    a = pubmed.NCBI_search()
    try:
        pmcids = a.query(query, db='pmc', onlyFreetext=onlyFreetext, onlyOAC=onlyOAC)
    except:
        return _error('Error while calling NCBI search. Try again later.')
    pmcids = ['PMC' + x for x in pmcids]

    if not pmcids:
        return JsonResponse({'status': True,
                             'pmchits': 0,
                             'indb': 0})

    indb = Article.objects.filter(pmcid__in=pmcids).count()
    return JsonResponse({'status': True,
                         'pmchits': len(pmcids),
                         'indb': indb})


@ratelimit(key='ip', method=ratelimit.ALL, rate='1/10s')
@ratelimit(key='ip', method=ratelimit.ALL, rate='5/m')
@ratelimit(key='ip', method=ratelimit.ALL, rate='30/h')
@ratelimit(key='ip', method=ratelimit.ALL, rate='200/d')
def api(request):
    was_limited = getattr(request, 'limited', False)
    if was_limited:
        return _error('Request blocked due to rate limiting. The rates are: 1 per 10 seconds, 5 per minute, 30 per hour, 200 per day')

    if request.method != 'POST':
        return _error('Invalid request')

    d = request.POST
    query = d.get('q', '')
    pubtype = d.get('st', '')
    tags = d.get('t', '')
    nonempty = d.get('t', '')
    ignoretags = d.get('it', '')
    docclass = d.get('cl', '')
    samplesize = d.get('ss', '')

    if not query or not pubtype or pubtype not in [x[0] for x in PUBTYPES]:
        return _error('Invalid request')

    tags = [x.strip() for x in tags.split(',') if x.strip()]
    ignoretags = [x.strip() for x in ignoretags.split(',') if x.strip()]
    if pubtype == 'free':
        onlyFreetext = True
        onlyOAC = False
    elif pubtype == 'oac':
        onlyFreetext = False
        onlyOAC = True

    a = pubmed.NCBI_search()
    try:
        pmcids = a.query(query, db='pmc', onlyFreetext=onlyFreetext, onlyOAC=onlyOAC)
    except:
        return _error('Error while calling NCBI search. Try again later.')
    pmcids = ['PMC' + x for x in pmcids]

    if samplesize:
        pmcids = sample(pmcids, int(samplesize))

    if not pmcids:
        return JsonResponse({'status': True,
                             'pmchits': 0,
                             'empty': 0,
                             'exported': 0,
                             'indb': 0,
                             'fsize': 0,
                             'fname': 0})

    start = time()

    k = psutil.cpu_count()
    N = len(pmcids)
    blockSize = max(min(50, N//k), 1)
    proc_pool = [TextExtractor(tags, ignoretags, nonempty, docclass) for i in range(k)]
    for p in proc_pool:
        p.start()

    # archive with original xml data
    base_fname = os.path.join(settings.MEDIA_ROOT, datetime.now().strftime('%a-%d-%b-%Y-%H-%M-%S-%f'))
    xml_archive_fpath = base_fname + '.xml.zip'
    xml_archive = zipfile.ZipFile(xml_archive_fpath, mode='w', compression=zipfile.ZIP_DEFLATED)

    indb = 0
    while len(pmcids) > 0:
        # this scheduler may not get the accurate qsizes but may still be better than random
        workloads = [p.workQueue.qsize() for p in proc_pool]
        minload = min(workloads)
        if minload > 20:
            sleep(1)
            continue

        free = workloads.index(minload)
        idsblock = pmcids[:blockSize]
        del pmcids[:blockSize]
        data = Article.objects.filter(pmcid__in=idsblock).values_list('pmcid', 'xml')
        indb += len(data)  # this also forces database access
        proc_pool[free].workQueue.put(data)

        # also dump xml files into the archive
        for adata in data:
            xml_archive.writestr('{}.xml'.format(adata[0]), adata[1])
    xml_archive.close()

    # print('sending stop signal')
    for p in proc_pool:
        p.workQueue.put(SENTINEL)

    # print('joining')
    for p in proc_pool:
        p.join()
    # print('processing finished')

    empty = 0
    nwritten = 0
    fpath = base_fname + '.lndoc'
    with open(fpath, 'w') as ofp:
        for p in proc_pool:
            variables = p.variables.get()
            empty += variables['nempty']
            nwritten += variables['nwritten']
            # print(variables)
            with open(variables['fname']) as pfp:
                ofp.write(pfp.read())

    # if samplesize:
    #     # shuf -n 1000 -o outdfile infile

    print('total time {:.1f}'.format(time()-start))

    zfpath = fpath + '.zip'
    #with zipfile.ZipFile(zfpath, mode='w', compression=zipfile.ZIP_BZIP2) as fz:
    with zipfile.ZipFile(zfpath, mode='w', compression=zipfile.ZIP_DEFLATED) as fz:
        fz.write(fpath, arcname=os.path.basename(fpath))
    os.remove(fpath)

    fsize = os.path.getsize(zfpath)
    fsize = '{:.0f} MB'.format(fsize/1e6) if fsize > 1e6 else '{:.0f} KB'.format(fsize/1e3)

    xmlfsize = os.path.getsize(xml_archive_fpath)
    xmlfsize = '{:.0f} MB'.format(xmlfsize/1e6) if xmlfsize > 1e6 else '{:.0f} KB'.format(xmlfsize/1e3)

    return JsonResponse({'status': True,
                         'pmchits': N,
                         'empty': empty,
                         'exported': nwritten,
                         'indb': indb,
                         'fsize': fsize,
                         'fname': os.path.split(zfpath)[1],
                         'xmlfsize': xmlfsize,
                         'xmlzip': os.path.split(xml_archive_fpath)[1]
                         })
