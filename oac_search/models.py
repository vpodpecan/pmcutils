from django.db import models

# Create your models here.


class Archive(models.Model):
    name = models.CharField(max_length=50, verbose_name='archive file')
    date = models.DateTimeField(verbose_name='archive file creation date')

    def __str__(self):
        return str(self.name)


class Article(models.Model):
    pmcid = models.CharField(max_length=20, unique=True, verbose_name='Pubmed Central ID')
    path = models.CharField(max_length=200, verbose_name='file path')
    xml = models.TextField(blank=True, verbose_name='XML content')
    text = models.TextField(blank=True, verbose_name='full text')
    cleantext = models.TextField(blank=True, verbose_name='text without figures, tables, etc.')
    archive = models.ForeignKey(Archive, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return str(self.pmcid)
