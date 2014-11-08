from django.contrib import messages
from django.http import (HttpResponse,
                         HttpResponseForbidden, 
                         HttpResponseNotFound)
from django.shortcuts import redirect 
from djangohelpers import (rendered_with,
                           allow_http)
from actionkit.models import CoreAction
from main.models import TaskBatch
from djcelery.models import TaskState
from main.forms import *
from actionkit import *

from django.db import connections

from main.tasks import run_batch_job
from main.models import BatchJob, JobTask


import csv
import io

@allow_http("GET", "POST")
@rendered_with("main/batch_job.html")
def batch_job(request, type):
    job = BatchJob(created_by=request.user, type=type)
    
    if request.method == "GET":
        form = job.form_factory(data=request.GET)
    else:
        form = job.form_factory(data=request.POST)

    if not form.is_valid():
        preview = False
        return locals()        
    job = form.fill_job(job)

    if request.method == "GET":
        _rows = job.run_sql()
        limit = request.GET.get("limit", 100)
        rows = []
        while len(rows) < limit:
            try:
                rows.append(_rows.next())
            except StopIteration:
                break
        preview = True
        return locals()

    import json
    rows = request.POST['records']
    
    job.save()

    task = JobTask(parent_job=job)
    task.save()

    run_batch_job.delay(task)

    resp = redirect(".")
    resp['Location'] += '?' + request.META['QUERY_STRING']
    return resp

@allow_http("GET", "POST")
@rendered_with("main/home.html")
def home(request):
    links = []
    for job_type in BatchJob.TYPE_CHOICES:
        links.append(("/batch-job/%s/" % job_type[0], job_type[1]))
    return locals()
