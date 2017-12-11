from bs4 import BeautifulSoup as bs


with open('BMJ_2008_Oct_21_337_a2002.nxml') as fp:
    root = bs(fp, 'xml')

aid = root.find('article-id', attrs={'pub-id-type': 'pmc'})
if aid is not None:
    pmcid = aid.text.strip()
    if not pmcid.startswith('PMC'):
        pmcid = 'PMC' + pmcid
    print(pmcid)
