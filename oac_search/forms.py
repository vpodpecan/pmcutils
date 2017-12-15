from django import forms


PUBTYPES = [('free', 'free fulltext articles'), ('oac', 'open access subset of free articles (OAC)')]

class SearchForm(forms.Form):
    query = forms.CharField(label='PubMed Central (PMC) query', max_length=1000, required=True,
                            widget=forms.Textarea(attrs={'placeholder': 'query string', 'rows': 4}))
    tags = forms.CharField(label='XML tags to take text from (leave empty for all)', max_length=1000, required=False,
                            widget=forms.TextInput(attrs={'placeholder': 'for example: abstract, body'}))
    ignoretags = forms.CharField(label='XML tags to ignore (leave empty for nothing)',  max_length=1000, required=False,
                            widget=forms.TextInput(attrs={'placeholder': 'for example: back, xref'}))
    nonempty = forms.BooleanField(label='do not return empty XML extraction results (documents)', required=False, initial=True)
    pubtype = forms.ChoiceField(label='PMC article subset', widget=forms.RadioSelect, choices=PUBTYPES, initial=PUBTYPES[1][0])
