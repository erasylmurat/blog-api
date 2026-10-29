from collections.abc import Callable
from pathlib import Path

from django.http import HttpRequest
from django.urls import reverse_lazy
from django.utils.module_loading import import_string

from settings import conf

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = conf.SECRET_KEY

ALLOWED_HOSTS = conf.ALLOWED_HOSTS

AUTH_USER_MODEL = 'auths.User'

INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'apps.auths',
    'apps.blog',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'settings.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'settings.wsgi.application'
ASGI_APPLICATION = 'settings.asgi.application'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging
LOGS_DIR = BASE_DIR / 'logs'
LOG_FILE_NAME = 'blog.log'
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024
LOG_FILE_BACKUP_COUNT = 3
LOG_LEVEL = 'INFO'
LOG_FORMAT = '{asctime} {levelname} {name} {message}'

LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': LOG_FORMAT,
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / LOG_FILE_NAME,
            'maxBytes': LOG_FILE_MAX_BYTES,
            'backupCount': LOG_FILE_BACKUP_COUNT,
            'formatter': 'default',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': LOG_LEVEL,
    },
}

# Django Unfold (admin theme)
GITHUB_REPO_URL = 'https://github.com/erasylmurat/blog-api'
UNFOLD_DOCS_URL = 'https://unfoldadmin.com/docs/'
CALLBACKS = 'apps.blog.callbacks'


def _callback(name: str) -> Callable[[HttpRequest], object]:
    """Lazy wrapper: models can't be imported while settings load."""

    def wrapper(request: HttpRequest) -> object:
        return import_string(f'{CALLBACKS}.{name}')(request)

    return wrapper


UNFOLD = {
    'SITE_TITLE': 'Blog API Admin',
    'SITE_HEADER': 'Blog API',
    'SITE_SUBHEADER': 'Content management',
    'SITE_SYMBOL': 'article',
    'SITE_URL': '/admin/',
    'ENVIRONMENT': f'{CALLBACKS}.environment_callback',
    'DASHBOARD_CALLBACK': f'{CALLBACKS}.dashboard_callback',
    'COLORS': {
        # Tailwind "blue" palette
        'primary': {
            '50': 'oklch(97% 0.014 254.604)',
            '100': 'oklch(93.2% 0.032 255.585)',
            '200': 'oklch(88.2% 0.059 254.128)',
            '300': 'oklch(80.9% 0.105 251.813)',
            '400': 'oklch(70.7% 0.165 254.624)',
            '500': 'oklch(62.3% 0.214 259.815)',
            '600': 'oklch(54.6% 0.245 262.881)',
            '700': 'oklch(48.8% 0.243 264.376)',
            '800': 'oklch(42.4% 0.199 265.638)',
            '900': 'oklch(37.9% 0.146 265.522)',
            '950': 'oklch(28.2% 0.091 267.935)',
        },
    },
    'SITE_DROPDOWN': [
        {
            'icon': 'code',
            'title': 'GitHub repository',
            'link': GITHUB_REPO_URL,
            'attrs': {'target': '_blank'},
        },
        {
            'icon': 'menu_book',
            'title': 'Unfold docs',
            'link': UNFOLD_DOCS_URL,
            'attrs': {'target': '_blank'},
        },
    ],
    'COMMAND': {
        'search_models': True,
        'show_history': True,
    },
    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': False,
        'navigation': [
            {
                'title': 'Overview',
                'items': [
                    {
                        'title': 'Dashboard',
                        'icon': 'dashboard',
                        'link': reverse_lazy('admin:index'),
                    },
                ],
            },
            {
                'title': 'Content',
                'items': [
                    {
                        'title': 'Posts',
                        'icon': 'article',
                        'link': reverse_lazy('admin:blog_post_changelist'),
                        'badge': f'{CALLBACKS}.drafts_badge',
                    },
                    {
                        'title': 'Comments',
                        'icon': 'forum',
                        'link': reverse_lazy('admin:blog_comment_changelist'),
                    },
                    {
                        'title': 'Categories',
                        'icon': 'category',
                        'link': reverse_lazy('admin:blog_category_changelist'),
                    },
                    {
                        'title': 'Tags',
                        'icon': 'sell',
                        'link': reverse_lazy('admin:blog_tag_changelist'),
                    },
                ],
            },
            {
                'title': 'Users & Access',
                'items': [
                    {
                        'title': 'Users',
                        'icon': 'person',
                        'link': reverse_lazy('admin:auths_user_changelist'),
                        'permission': f'{CALLBACKS}.is_superuser',
                    },
                    {
                        'title': 'Groups',
                        'icon': 'groups',
                        'link': reverse_lazy('admin:auth_group_changelist'),
                        'permission': f'{CALLBACKS}.is_superuser',
                    },
                ],
            },
        ],
    },
    'TABS': [
        {
            'models': ['blog.post'],
            'items': [
                {
                    'title': 'All',
                    'link': _callback('posts_all_link'),
                    'active': _callback('posts_all_active'),
                },
                {
                    'title': 'Published',
                    'link': _callback('posts_published_link'),
                    'active': _callback('posts_published_active'),
                },
                {
                    'title': 'Drafts',
                    'link': _callback('posts_drafts_link'),
                    'active': _callback('posts_drafts_active'),
                },
            ],
        },
    ],
}
