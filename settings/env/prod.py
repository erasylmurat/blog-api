from settings import conf
from settings.base import *  # noqa: F403

POSTGRES_ENGINE = 'django.db.backends.postgresql'

DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': POSTGRES_ENGINE,
        'NAME': conf.DB_NAME,
        'USER': conf.DB_USER,
        'PASSWORD': conf.DB_PASSWORD,
        'HOST': conf.DB_HOST,
        'PORT': conf.DB_PORT,
    }
}