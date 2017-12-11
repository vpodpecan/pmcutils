from django import forms


PUBTYPES = [('free', 'free fulltext articles'), ('oac', 'open access subset of free articles (OAC)')]

class SearchForm(forms.Form):
    query = forms.CharField(label='PubMed Central (PMC) query', max_length=1000, required=True,
                            widget=forms.Textarea(attrs={'placeholder': 'query string'}))
    tags = forms.CharField(label='XML tags to take text from (leave empty for all)', max_length=1000, required=False,
                            widget=forms.TextInput(attrs={'placeholder': 'for example: abstract, body'}))
    ignoretags = forms.CharField(label='XML tags to ignore (leave empty for nothing)',  max_length=1000, required=False,
                            widget=forms.TextInput(attrs={'placeholder': 'for example: front, back, xref'}))
    pubtype = forms.ChoiceField(label='PMC article subset', widget=forms.RadioSelect, choices=PUBTYPES, initial=PUBTYPES[1][0])
