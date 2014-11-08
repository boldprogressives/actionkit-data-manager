from django.db import models
from django.db import connections
from djcelery.models import TaskState
import decimal

from main import task_registry

# Create your models here.
#select * from core_action where user_id=1195198;

class BatchJob(models.Model):
    created_by = models.ForeignKey('auth.User')
    created_on = models.DateTimeField(auto_now_add=True)
    sql = models.TextField()
    form_data = models.TextField(default="{}")

    title = models.CharField(max_length=255, null=True, blank=True)

    def __unicode__(self):
        if self.title:
            return self.title
        else:
            return u"A %s created by %s on %s" % (self.type, self.created_by, self.created_on)

    TYPE_CHOICES = [
        (task.slug, task.description) for task in task_registry.tasks.values() #@@TODO
        ]

    type = models.CharField(max_length=255, choices=TYPE_CHOICES)

    @property
    def form_factory(self):
        return task_registry.get_task(self.type).form_class

    def get_form(self):
        return self.form_factory.from_job(self)

    def run_sql(self):
        cursor = connections['ak'].cursor()
        sql = self.sql
        cursor.execute(sql)

        row = cursor.fetchone()
        while row:
            row = [float(i) if isinstance(i, decimal.Decimal) else i for i in row]
            yield dict(zip([i[0] for i in cursor.description], row))
            row = cursor.fetchone()

class RecurringTask(models.Model):
    parent_job = models.ForeignKey(BatchJob)
    period = models.IntegerField()
    TIME_CHOICES = (
        ("minutes", "minutes"),
        ("hours", "hours"),
        ("days", "days"),
        )
    period_unit = models.CharField(max_length=255, choices=TIME_CHOICES)

    created_on = models.DateTimeField(auto_now_add=True)
    last_started_on = models.DateTimeField(null=True, blank=True)

    is_running = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __unicode__(self):
        return u"Every %s %s: %s" % (self.period, self.period_unit, unicode(self.parent_job))

    def reset(self):
        self.is_running = False
        self.save()

    def latest_run(self):
        return JobTask.objects.filter(parent_recurring_task=self).order_by("-created_on")[0]

    def stale_runs(self):
        """ 
        Returns all but the most recent two runs of this job.
        """
        runs = JobTask.objects.filter(parent_recurring_task=self).order_by("created_on")
        runs = list(runs)
        return runs[:-2]

class JobTask(models.Model):
    parent_job = models.ForeignKey(BatchJob, null=True, blank=True)
    parent_recurring_task = models.ForeignKey(RecurringTask,
                                              null=True, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    completed_on = models.DateTimeField(null=True, blank=True)

    num_rows = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)

    def __unicode__(self):
        job = self.parent_job
        task = self.parent_recurring_task
        if task is not None:
            job = task.parent_job

        return "(job:%s) task:%s" % (unicode(job), self.id)

from djangohelpers.lib import register_admin
register_admin(BatchJob)
register_admin(RecurringTask)
register_admin(JobTask)

class TaskBatch(models.Model):
    tasks = models.TextField(null=True, blank=True)

    def add_task(self, task):
        if not self.tasks:
            self.tasks = str(task)
        else:
            self.tasks = self.tasks + "," + str(task)
        self.save()

    def get_tasks(self):
        if not self.tasks:
            return []
        tasks = self.tasks.split(",")
        return TaskState.objects.using("celerytasks").filter(task_id__in=tasks)

    @models.permalink
    def get_absolute_url(self):
        return ("batch", [self.id])
