from main.forms import BatchForm, activity_log, sql_log, success_log, error_log
from django import forms
from actionkit import Client
from actionkit.rest import client as RestClient
from actionkit.models import CoreAction, CoreActionField

class UserfieldJobForm(BatchForm):
    help_text = """
The SQL must return a column named `user_id`. Userfield Value is optional -- include it if you want a hardcoded userfield value filled in for all results. Alternatively, you can cause the SQL to return a column named `userfield_value`, and this will be used instead.
"""
    userfield_name = forms.CharField(label="Userfield Name", required=True)
    userfield_value = forms.CharField(label="Userfield Value", required=False)
    action_page = forms.CharField(label="Page Names to Act On", required=False)

    def run(self, task, rows):
        userfield_value = self.cleaned_data.get("userfield_value").strip() or None
        userfield_name = self.cleaned_data['userfield_name']

        page = self.cleaned_data.get('action_page', '').strip() or None

        ak = Client()
        rest = RestClient()
        rest.safety_net = False

        userfield_name = 'user_%s' % userfield_name

        n_rows = n_success = n_error = 0

        for row in rows:
            sql_log("%s %s" % (unicode(task), row))
            n_rows += 1
            assert row.get('user_id') and int(row['user_id'])

            if page:
                try:
                    action = CoreAction.objects.using("ak").select_related(
                        "page").get(
                        user__id=row['user_id'], page__name=page)
                except CoreAction.DoesNotExist:
                    action = None
                except CoreAction.MultipleObjectsReturned:
                    action = None
            else:
                action = None

            try:
                if page is None:
                    resp = ak.User.save({
                            "id": row['user_id'],
                            userfield_name: (userfield_value or
                                             row['userfield_value'])})
                elif action is None:
                    resp = ak.act({
                            "id": row['user_id'],
                            "page": page,
                            "source": "aktasks-%s" % task.id,
                            userfield_name: (userfield_value or
                                             row['userfield_value'])})
                else:
                    page_url = "/rest/v1/%spage/%s/" % (
                        action.page.type.lower(), action.page_id)
                    user_url = "/rest/v1/user/%s/" % action.user_id
                    handler = getattr(
                        rest, "%saction" % action.page.type.lower())
                    args = dict(page=page_url, user=user_url)
                    args[userfield_name] = (userfield_value or
                                            row['userfield_value'])
                    args['source'] = "aktasks-%s" % task.id
                    handler.put(action.id, **args)
                                

                resp['log_id'] = row['user_id']
                success_log("%s %s" % (unicode(task), resp))
            except Exception, e:
                n_error += 1
                resp = {}
                resp['log_id'] = row['user_id']
                resp['error'] = traceback.format_exc()
                error_log("%s %s" % (unicode(task), resp))
            else:
                n_success += 1

        return n_rows, n_success, n_error

class ActionfieldRenameJobForm(BatchForm):
    help_text = """
The SQL must return a column named `actionfield_id`. New Actionfield Name is optional -- include it if you want all results renamed to the same thing.  Alternatively, you can cause the SQL to return a column named `new_actionfield_name`, and this will be used instead.  If your SQL returns a column named `new_actionfield_value`, or if you fill out the New Actionfield Value field, then actionfields will have their values updated as well.  If you leave this form field blank and do not return this column, the actionfield values will not be changed.
"""
    new_actionfield_name = forms.CharField(label="New Actionfield Name", 
                                           required=False)
    new_actionfield_value = forms.CharField(label="New Actionfield Value", 
                                           required=False)

    def run(self, task, rows):
        new_actionfield_name = self.cleaned_data.get(
            "new_actionfield_name").strip() or None
        new_actionfield_value = self.cleaned_data.get(
            "new_actionfield_value").strip() or None

        rest = RestClient()
        rest.safety_net = False

        n_rows = n_success = n_error = 0

        for row in rows:
            sql_log("%s %s" % (unicode(task), row))
            n_rows += 1
            assert row.get("actionfield_id") and int(row['actionfield_id'])

            actionfield = CoreActionField.objects.using("ak").select_related(
                "parent", "parent__page").get(
                id=row['actionfield_id'])
            data = {
                'parent': "/rest/v1/%saction/%s/" % (
                    actionfield.parent.page.type.lower(), 
                    actionfield.parent.id),
                'name': (new_actionfield_name
                         or row['new_actionfield_name']),
                'value': (new_actionfield_value 
                          or row.get('new_actionfield_value')
                          or actionfield.value),
                }
            try:
                resp = rest.actionfield.put(actionfield.id, **data)
                resp['log_id'] = row['actionfield_id']
                success_log("%s %s" % (unicode(task), resp))
            except Exception, e:
                n_error += 1
                resp = {}
                resp['log_id'] = row['actionfield_id']
                resp['error'] = traceback.format_exc()
                error_log("%s %s" % (unicode(task), resp))
            else:
                n_success += 1

        return n_rows, n_success, n_error

class UnsubscribeAndActJobForm(BatchForm):
    help_text = """
<p>The SQL must return a column named `user_id`.</p>

<p>If the SQL returns a column named `caused_by_action`, the value of this column
will be stored in a custom actionfield `caused_by_action` on the action page that
each user is marked as acting on.</p>

<p>If unsubscribe_lists is not set, no unsubscriptions will occur.</p>
"""

    unsubscribe_lists = forms.CharField(label="List IDs to Unsubscribe From",
                                        required=False)
    action_page = forms.CharField(label="Page Names to Act On", required=False)

    def run(self, task, rows):
        lists = self.cleaned_data.get('unsubscribe_lists') or ""
        lists = [int(i.strip()) for i in lists.split(",") if i]
        page = self.cleaned_data.get('action_page', '').strip() or None

        ak = Client()

        n_rows = n_success = n_error = 0

        for row in rows:
            sql_log("%s: %s" % (unicode(task), row))
            n_rows += 1
            assert row.get('user_id') and int(row['user_id'])
            user_id = row['user_id']

            caused_by_action = row.get('caused_by_action') or None
            unsubs = []
            for list_id in lists:
                try:
                    ak.User.unsubscribe({'id': user_id, 'list_id': list_id})
                except:
                    pass
                else:
                    unsubs.append(list_id)
            if page is None:
                continue
            action = {'id': user_id, 'page': page}
            if unsubs:
                action['action_unsubscribed_from_lists'] = unsubs
            if caused_by_action:
                action['action_caused_by_action'] = caused_by_action
            try:
                resp = ak.act(action)
                resp['log_id'] = row['user_id']
                success_log("%s %s" % (unicode(task), resp))
            except Exception, e:
                n_error += 1
                resp = {}
                resp['log_id'] = row['user_id']
                resp['error'] = traceback.format_exc()
                error_log("%s %s" % (unicode(task), resp))
            else:
                n_success += 1

        return n_rows, n_success, n_error
