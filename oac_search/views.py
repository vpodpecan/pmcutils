import tempfile
import zipfile
import os
import unidecode
from multiprocessing import Pool
import psutil
import itertools
from time import time
from datetime import datetime
from hashlib import sha1

from bs4 import BeautifulSoup as bs
from ratelimit.decorators import ratelimit

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.generic import TemplateView, View
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from oac_search.forms import PUBTYPES, SearchForm
from oac_search import pubmed_oac as pubmed
from oac_search.models import Archive, Article


def _error(message):
    return JsonResponse({'status': False, 'message': message})


def index(request):
    # if request.method == 'GET':
    context = {'form': SearchForm(initial={'pubtype': PUBTYPES[1][0]}),
               'archives': Archive.objects.all().order_by('name'),
               'narticles': Article.objects.count()}
    return render(request, 'oac_search/index.html', context)
    # else:
    #     form = SearchForm(request.POST)
    #     if form.is_valid():
    #         params = form.cleaned_data
    #         query = params['query']
    #         pubtype = params['pubtype']
    #         return render(request, 'oac_search/index.html', {'form': form, 'hits': pmcids})


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

    a = pubmed.NCBI_Extractor()
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

    a = pubmed.NCBI_Extractor()
    try:
        pmcids = a.query(query, db='pmc', onlyFreetext=onlyFreetext, onlyOAC=onlyOAC)
    except:
        return _error('Error while calling NCBI search. Try again later.')
    pmcids = ['PMC' + x for x in pmcids]

    if not pmcids:
        return JsonResponse({'status': True,
                             'pmchits': 0,
                             'empty': 0,
                             'exported': 0,
                             'indb': 0,
                             'fsize': 0,
                             'fname': 0})

    start = time()

    # poolSize = max(1, int(psutil.cpu_count()/2))
    poolSize = psutil.cpu_count()
    chunkSize = int(len(pmcids)**0.5 / 2)   # min(len(pmcids) // poolSize, 1000)
    print('pool and chunk size: ', poolSize, chunkSize)
    # pool = Pool(psutil.cpu_count())
    pool = Pool(poolSize)
    fpath = os.path.join(settings.MEDIA_ROOT, datetime.now().strftime('%a-%d-%b-%Y-%H-%M-%S-%f') + '.lndoc')
    # fp, fpath = tempfile.mkstemp(suffix='.lndoc', prefix=datetime.now().strftime('%a-%d-%b-%Y-%H-%M-%S-%f') + '--', dir=settings.MEDIA_ROOT)
    with open(fpath, 'w') as ofp:
        cnt = 0
        empty = 0
        nwritten = 0

        for pmcid, text in pool.starmap(_get_article_text_fast, zip(itertools.repeat((tags, ignoretags)), Article.objects.filter(pmcid__in=pmcids).values('pmcid', 'xml').iterator()), chunksize=chunkSize):  # 500 je ok
        # for article in Article.objects.filter(pmcid__in=pmcids).iterator():
            cnt += 1
            # pmcid, text = _get_article_text((tags, ignoretags), article)
            if text == '':
                empty += 1
                if nonempty:
                    continue
            line = '{}\t{}\n'.format(pmcid, text)
            ofp.write(line)
            nwritten += 1

    print('total time {:.1f}'.format(time()-start))

    zfpath = fpath + '.zip'
    with zipfile.ZipFile(zfpath, mode='w', compression=zipfile.ZIP_BZIP2) as fz:
        fz.write(fpath)
    os.remove(fpath)

    fsize = os.path.getsize(zfpath)
    fsize = '{:.0f} MB'.format(fsize/1e6) if fsize > 1e6 else '{:.0f} KB'.format(fsize/1e3)
    return JsonResponse({'status': True,
                         'pmchits': len(pmcids),
                         'empty': empty,
                         'exported': nwritten,
                         'indb': cnt,
                         'fsize': fsize,
                         'fname': os.path.split(zfpath)[1]
                         })
