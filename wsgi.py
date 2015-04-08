import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

import dotenv
dotenv.read_dotenv()

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
