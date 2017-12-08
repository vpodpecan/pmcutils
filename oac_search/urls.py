from django.conf.urls import url

from oac_search import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
]
