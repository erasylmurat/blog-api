from settings import conf
from settings.base import *  # noqa: F403
from settings.base import BASE_DIR, LOGGING

SQLITE_ENGINE = 'django.db.backends.sqlite3'
SQLITE_DB_NAME = 'db.sqlite3'

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': SQLITE_ENGINE,
        'NAME': BASE_DIR / SQLITE_DB_NAME,
    }
}

# SQL query logging (BLOG_SQL_LOG=True in .env) - used to check for N+1
SQL_LOGGER = 'django.db.backends'
SQL_LOG_LEVEL_ON = 'DEBUG'
SQL_LOG_LEVEL_OFF = 'INFO'

LOGGING['loggers'] = {
    SQL_LOGGER: {
        'handlers': ['console'],
        'level': SQL_LOG_LEVEL_ON if conf.SQL_LOG else SQL_LOG_LEVEL_OFF,
        'propagate': False,
    },
}
