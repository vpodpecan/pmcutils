from django import forms


PUBTYPES = [('free', 'free fulltext articles'), ('oac', 'open access subset of free articles (OAC)')]

class SearchForm(forms.Form):
    query = forms.CharField(label='PubMed Central (PMC) query', max_length=1000, required=True,
                            widget=forms.Textarea(attrs={'placeholder': 'query string'}))
    # xmltags = forms.CharField(label='XML tags to extract text from')
    pubtype = forms.ChoiceField(label='PMC article subset', widget=forms.RadioSelect, choices=PUBTYPES, initial=PUBTYPES[1][0])
    # freetext = forms.BooleanField(label='only free fulltext articles')
    # oac = forms.BooleanField(label='only open access articles (a subset of free fulltext)')
