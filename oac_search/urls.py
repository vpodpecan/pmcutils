from django.conf.urls import url

from oac_search import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^api', views.api, name='api'),
    url(r'^ask', views.api_query, name='ask'),
]
