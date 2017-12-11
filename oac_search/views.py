import tempfile
import os
import unidecode
from multiprocessing import Pool
import psutil
import itertools

from bs4 import BeautifulSoup as bs

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
        _ = [x.extract() for x in root.find_all(tag)]

    for t in tags:
        parts = [x.get_text(separator=u' ') for x in root.find_all(t)]

    parts = [x.get_text(separator=u' ') for x in root.find_all()]

    text = root.get_text(separator=u' ').strip().replace('\n', ' ').replace('\t', ' ').replace('  ', ' ').replace('  ', ' ')
    return text





    return article.pmcid, unidecode.unidecode(article.cleantext)


def api(request):

    if request.method != 'POST':
        return _error('Invalid request')

    d = request.POST
    print(d)
    query = d.get('q', '')
    pubtype = d.get('st', '')
    tags = d.get('t', '')
    ignoretags = d.get('it', '')

    if not query or not pubtype or pubtype not in [x[0] for x in PUBTYPES]:
        return _error('Invalid request')

    tags = [x.strip() for x in tags.split(',')]
    ignoretags = [x.strip() for x in ignoretags.split(',')]
    if pubtype == 'free':
        onlyFreetext = True
        onlyOAC = False
    elif pubtype == 'oac':
        onlyFreetext = False
        onlyOAC = True

    a = pubmed.NCBI_Extractor()
    pmcids = a.query(query, db='pmc', onlyFreetext=onlyFreetext, onlyOAC=onlyOAC)
    pmcids = ['PMC' + x for x in pmcids]

    if not pmcids:
        return JsonResponse({'status': True, 'n': 0})

    pool = Pool(psutil.cpu_count(logical=False))
    fp, fpath = tempfile.mkstemp(suffix='.lndoc', dir=settings.MEDIA_ROOT)
    with open(fp, 'w') as ofp:
        cnt = 0
        # for pmcid, text in pool.imap(_get_article_text, Article.objects.filter(pmcid__in=pmcids).iterator(), chunksize=100):
        for pmcid, text in pool.starmap(_get_article_text, zip(itertools.repeat((tags, ignoretags)), Article.objects.filter(pmcid__in=pmcids).iterator()), chunksize=100):
            line = '{}\t{}\n'.format(pmcid, text)
            ofp.write(line)
            cnt += 1



    # fp, fpath = tempfile.mkstemp(suffix='.lndoc', dir=settings.MEDIA_ROOT)
    # with open(fp, 'w') as ofp:
    #     cnt = 0
    #     for article in Article.objects.filter(pmcid__in=pmcids).iterator():
    #         line = '{}\t{}\n'.format(article.pmcid, unidecode.unidecode(article.cleantext))
    #         ofp.write(line)
    #         cnt += 1
    print(len(pmcids), cnt, fpath)
    return JsonResponse({'status': True, 'n': cnt, 'f': fpath})
