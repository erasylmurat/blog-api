import os

from django.core.wsgi import get_wsgi_application

from settings import conf

os.environ.setdefault(
    conf.DJANGO_SETTINGS_MODULE_ENV_VAR,
    conf.SETTINGS_MODULE,
)

application = get_wsgi_application()
