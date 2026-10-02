import os

from django.core.asgi import get_asgi_application

from settings import conf

os.environ.setdefault(
    conf.DJANGO_SETTINGS_MODULE_ENV_VAR,
    conf.SETTINGS_MODULE,
)

application = get_asgi_application()
