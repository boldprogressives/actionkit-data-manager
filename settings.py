import os
SITE_DOMAIN = os.environ['SITE_DOMAIN']

# Django settings for skel project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = [
    ("Admin", i) for i in os.environ['ADMIN_EMAILS'].split(",")
]

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en-us'

INTERNAL_IPS = ('127.0.0.1',
                )

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# By default urllib, urllib2, and the like have no timeout which can cause
# some apache processes to hang until they are forced kill.
# Before python 2.6, the only way to cause them to time out is by setting
# the default timeout on the global socket
import socket
socket.setdefaulttimeout(5)

import os
PROJECT_PATH = os.path.realpath(os.path.dirname(__file__))
MEDIA_ROOT = os.path.join(PROJECT_PATH, 'media/')
STATIC_ROOT = os.path.join(PROJECT_PATH, 'static/')
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(PROJECT_PATH, 'common_static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DEFAULT_FROM_EMAIL = os.environ['DEFAULT_FROM_EMAIL']

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'djangohelpers.middleware.AuthRequirementMiddleware',
)

ANONYMOUS_PATHS = ['/static/', '/admin/', '/accounts/']

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_PATH, "templates"),
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.flatpages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'dbtemplates',
    'debug_toolbar',
    'djangohelpers',
    'djsupervisor',
    'djcelery',
    'basic_tasks',
    'main',
    ]

TASKMAN_PLUGIN_PACKAGES = [i for i in os.environ.get("TASKMAN_PLUGIN_PACKAGES", "").split(",")
                           if i]
for app_name in TASKMAN_PLUGIN_PACKAGES:
    INSTALLED_APPS.append(app_name)
if 'TASKMAN_LOGGER_CLASS' in os.environ:
    TASKMAN_LOGGER_CLASS = os.environ['TASKMAN_LOGGER_CLASS']
    
TEMPLATE_LOADERS = (
    'dbtemplates.loader.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    "django.core.context_processors.request",
    )


import dj_database_url

DATABASES = {
    'default': dj_database_url.config(),
    'ak': dj_database_url.config(env="ACTIONKIT_DATABASE_URL"),
    }

import os
BROKER_HOST = os.environ['BROKER_HOST']
BROKER_PORT = os.environ['BROKER_PORT']
BROKER_USER = os.environ['BROKER_USER']
BROKER_PASSWORD = os.environ['BROKER_PASSWORD']
BROKER_VHOST = os.environ['BROKER_VHOST']

EMAIL_HOST = os.environ['EMAIL_HOST']
EMAIL_PORT = os.environ['EMAIL_PORT']
if 'EMAIL_HOST_USER' in os.environ:
    EMAIL_HOST_USER = os.environ['EMAIL_HOST_USER']
if 'EMAIL_HOST_PASSWORD' in os.environ:
    EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
if 'EMAIL_USE_TLS' in os.environ:
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS') == "True"

ACTIONKIT_API_HOST = os.environ['ACTIONKIT_API_HOST']
ACTIONKIT_API_USER = os.environ['ACTIONKIT_API_USER']
ACTIONKIT_API_PASSWORD = os.environ['ACTIONKIT_API_PASSWORD']

import importlib
for app_name in TASKMAN_PLUGIN_PACKAGES:
    try:
        d = importlib.import_module('%s.app_settings' % app_name)
        for value in getattr(d, 'export', []):
            globals()[value] = getattr(d, value)
    except Exception:
        pass

import djcelery
djcelery.setup_loader()
