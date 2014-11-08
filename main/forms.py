from datetime import datetime
from django import forms
from django.contrib.localflavor.us import forms as usforms
import traceback

from actionkit.models import CoreUser
import json

class JobError(RuntimeError):
    def __init__(self, errors):
        self.errors = errors

from django.utils.datastructures import SortedDict
from django.db import connections
def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        SortedDict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

import logging

logger = logging.getLogger('aktasks')

activity_log = logger.debug
sql_log = logger.info
success_log = logger.warn
error_log = logger.error

class BatchForm(forms.Form):
    help_text = ""
    sql = forms.CharField(widget=forms.Textarea, label="SQL", required=True)
    title = forms.CharField(label="Job Title", required=False)

    @classmethod
    def from_job(cls, job):
        import json
        data = json.loads(job.form_data)
        data['sql'] = job.sql

        form = cls(data=data)
        if not form.is_valid():
            raise JobError(form.errors)

        return form

    def fill_job(self, job):
        job.sql = self.cleaned_data['sql']
        if self.cleaned_data.get("title", "").strip():
            job.title = self.cleaned_data['title'].strip()

        import json
        cd = dict(self.cleaned_data)
        cd.pop('sql')
        job.form_data = json.dumps(cd)
        return job


class UserfieldJSONJobForm(BatchForm):
    help_text ="""
The SQL must return a column named `user_id` and must be ordered primarily by user_id, 
so that all rows associated with user A occur before any rows associated with user B, 
and so on.

The SQL must return a column named `actionfield_name` and another column 
named `actionfield_value`.  For each row, the `actionfield_value` column's 
value should be one of ("1", "y", "yes", "t", "true", "on", "checked") or one of
("0", "n", "no", "f", "false", "off", "unchecked") -- all other values will cause 
an error.  This column's value will determine whether the string in `actionfield_name` 
should be added or removed from the associated userfield.

The SQL should probably be secondarily sorted by core_action.created_at ASCENDING 
(i.e. earliest to most recent) within each user_id -- this isn't strictly necessary, 
but in most cases it's what will be wanted. (Rows returned later in the query will 
override earlier rows.)

For example, if the SQL returns these (ordered) results:

  user_id, actionfield_value, actionfield_name
  10, y, vol_phonecalls
  10, y, vol_knockdoors
  10, n, vol_phonecalls
  10, y, vol_phonecalls
  11, n, vol_phonecalls
  12, y, vol_phonecalls
  12, n, vol_phonecalls

then the resulting userfields will be:

  parent_id, value
  10, ["vol_phonecalls", "vol_knockdoors"]
  11, []
  12, []

Note that the order of the rows returned matters a lot.  I cannot stress this enough.
"""
    userfield_name = forms.CharField(label="Userfield Name", required=True)
    
    def run(self, task, rows):
        userfield_name = self.cleaned_data['userfield_name']

        from actionkit import Client
        from actionkit.rest import client as RestClient
        ak = Client()
        rest = RestClient()
        rest.safety_net = False

        userfield_name = 'user_%s' % userfield_name

        n_rows = n_success = n_error = 0

        accumulator = (None, set())
        for row in rows:
            sql_log("%s %s" % (unicode(task), row))
            n_rows += 1
            assert row.get('user_id') and int(row['user_id'])

            if accumulator[0] != row['user_id']:
                # It's time to update the last-before-now user!
                if accumulator[0] is not None:
                    try:
                        resp = ak.User.save({
                                "id": accumulator[0],
                                userfield_name: json.dumps(list(accumulator[1])),
                                })
                    except Exception, e:
                        n_error += 1
                        resp = {}
                        resp['log_id'] = accumulator[0]
                        resp['error'] = traceback.format_exc()
                        error_log("%s %s" % (unicode(task), resp))
                    else:
                        n_success += 1
                # Having done that, we'll reset the accumulator.
                accumulator = (row['user_id'], set())
            assert row.get("actionfield_name")
            assert row.get("actionfield_value") and row['actionfield_value'] in (
                "1", "y", "yes", "t", "true", "on", "checked",
                "0", "n", "no", "f", "false", "off", "unchecked",
                )
            if row['actionfield_value'] in ("1", "y", "yes", "t", "true", "on", "checked"):
                accumulator[1].add(row['actionfield_name'])
            else:
                if row['actionfield_name'] in accumulator[1]:
                    accumulator[1].remove(row['actionfield_name'])
                    
        if accumulator[0] is not None:
            try:
                resp = ak.User.save({
                        "id": accumulator[0],
                        userfield_name: json.dumps(list(accumulator[1])),
                        })
            except Exception, e:
                n_error += 1
                resp = {}
                resp['log_id'] = accumulator[0]
                resp['error'] = traceback.format_exc()
                error_log("%s %s" % (unicode(task), resp))
            else:
                n_success += 1
        return n_rows, n_success, n_error
            

class EventForm(forms.Form):
    title = forms.CharField(label="Title", required=False)
    date = forms.DateField(label="Date", required=False)
    time = forms.TimeField(label="Time", required=False)

    venue = forms.CharField(label="Venue", required=True)
    address = forms.CharField(label="Address", required=True)
    city = forms.CharField(label="City", required=True)
    state = usforms.USStateField(label="State", required=True)
    zip = usforms.USZipCodeField(label="ZIP", required=True)

    max_attendees = forms.IntegerField(label="Max Attendees", required=True)
    host = forms.EmailField(label="Host's Email Address", required=True)

    public_description = forms.CharField(label="Description", required=False, widget=forms.Textarea())
    directions = forms.CharField(label="Directions", required=False, widget=forms.Textarea())

    def clean_host(self):
        host = self.cleaned_data['host']
        try:
            user = CoreUser.objects.using("ak").get(email=host)
        except CoreUser.DoesNotExist:
            raise forms.ValidationError("No core_user exists with email %s" % host)
        return user

    def clean(self):
        try:
            data = self.build_event_struct()
        except:
            pass
        else:
            self.event_struct = data
        return self.cleaned_data

    def build_event_struct(self):
        data = {}
        for key in "title venue city state zip max_attendees".split():
            data[key] = self.cleaned_data.get(key)
        for key in "directions public_description".split():
            if key in self.cleaned_data and self.cleaned_data.get(key).strip():
                data[key] = self.cleaned_data.get(key)
        data['creator_id'] = self.cleaned_data['host'].id
        data['address1'] = self.cleaned_data['address']        
        data['starts_at'] = datetime.combine(self.cleaned_data['date'], self.cleaned_data['time'])
        return data
