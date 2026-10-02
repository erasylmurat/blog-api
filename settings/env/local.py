from settings.base import *  # noqa: F403
from settings.base import BASE_DIR

SQLITE_ENGINE = 'django.db.backends.sqlite3'
SQLITE_DB_NAME = 'db.sqlite3'

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': SQLITE_ENGINE,
        'NAME': BASE_DIR / SQLITE_DB_NAME,
    }
}
