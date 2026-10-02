from pathlib import Path

from decouple import AutoConfig, Csv

SETTINGS_DIR = Path(__file__).resolve().parent

config = AutoConfig(search_path=SETTINGS_DIR)

ENV_ID_LOCAL = 'local'
DJANGO_SETTINGS_MODULE_ENV_VAR = 'DJANGO_SETTINGS_MODULE'
SETTINGS_MODULE_TEMPLATE = 'settings.env.{env_id}'

DEFAULT_DB_NAME = 'blog'
DEFAULT_DB_USER = 'postgres'
DEFAULT_DB_HOST = 'localhost'
DEFAULT_DB_PORT = '5432'

SECRET_KEY: str = config('BLOG_SECRET_KEY')
ENV_ID: str = config('BLOG_ENV_ID', default=ENV_ID_LOCAL)
ALLOWED_HOSTS: list[str] = config(
    'BLOG_ALLOWED_HOSTS',
    default='',
    cast=Csv(),
)

DB_NAME: str = config('BLOG_DB_NAME', default=DEFAULT_DB_NAME)
DB_USER: str = config('BLOG_DB_USER', default=DEFAULT_DB_USER)
DB_PASSWORD: str = config('BLOG_DB_PASSWORD', default='')
DB_HOST: str = config('BLOG_DB_HOST', default=DEFAULT_DB_HOST)
DB_PORT: str = config('BLOG_DB_PORT', default=DEFAULT_DB_PORT)

SETTINGS_MODULE: str = SETTINGS_MODULE_TEMPLATE.format(env_id=ENV_ID)
