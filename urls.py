from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', 'main.views.home', name='home'),
    url(r'^batch-job/(?P<type>\w+)/$',
        'main.views.batch_job', 
        name='batch_job'),

    url(r'^admin/', include(admin.site.urls)),
    )

urlpatterns += patterns(
    'django.contrib.auth.views',
    (r'^accounts/login/$', 'login'),
    (r'^accounts/logout/$', 'logout'),
    )
