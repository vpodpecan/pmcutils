from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.generic import TemplateView, View
from django.views.decorators.csrf import csrf_exempt

from oac_search.forms import PUBTYPES, SearchForm
from oac_search import pubmed_oac as pubmed


def index(request):
    if request.method == 'GET':
        context = {'form': SearchForm(initial={'pubtype': PUBTYPES[1][0]})}
        return render(request, 'oac_search/index.html', context)
    else:
        form = SearchForm(request.POST)
        if form.is_valid():
            params = form.cleaned_data
            query = params['query']
            pubtype = params['pubtype']
            if pubtype == 'free':
                onlyFreetext = True
                onlyOAC = False
            elif pubtype == 'oac':
                onlyFreetext = False
                onlyOAC = True

            a = pubmed.NCBI_Extractor()
            pmcids = a.query(query, db='pmc', onlyFreetext=onlyFreetext, onlyOAC=onlyOAC)
            pmcids = ['PMC' + x for x in pmcids]
            print(' '.join(pmcids))
            return render(request, 'oac_search/index.html', {'form': form, 'hits': pmcids})


def api(request):
    if request.method == 'POST':
        d = request.POST
    elif request.method == 'GET':
        d = request.GET
    else:
        return JsonResponse({})

    n = int(d.get('n', 10))
    q = _get_query(d)
    if not q:
        return JsonResponse({})

    result = SimModel.query(q, n, enrichQuery=True)
    return JsonResponse({'lines': result})
