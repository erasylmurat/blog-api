import json
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import HttpRequest
from django.urls import reverse

from apps.blog.models import Category, Comment, Post
from settings import conf

User = get_user_model()

POST_CHANGELIST_URL = 'admin:blog_post_changelist'
STATUS_PARAM = 'status__exact'

ENV_PRODUCTION = 'prod'
ENV_BADGE_LOCAL = ['Local', 'warning']
ENV_BADGE_PRODUCTION = ['Production', 'danger']

TOP_AUTHORS_LIMIT = 5
NO_CATEGORY_LABEL = 'No category'
CHART_DATASET_LABEL = 'Posts'
CHART_COLOR = 'var(--color-primary-600)'
PERCENT = 100


# --- Environment badge -------------------------------------------------------


def environment_callback(request: HttpRequest) -> list[str]:
    if conf.ENV_ID == ENV_PRODUCTION:
        return ENV_BADGE_PRODUCTION
    return ENV_BADGE_LOCAL


# --- Sidebar -----------------------------------------------------------------


def drafts_badge(request: HttpRequest) -> str:
    drafts = Post.objects.filter(status=Post.Status.DRAFT).count()
    return str(drafts) if drafts else ''


def is_superuser(request: HttpRequest) -> bool:
    return request.user.is_superuser


# --- Post list tabs ----------------------------------------------------------


def _posts_url(status: str | None = None) -> str:
    url = reverse(POST_CHANGELIST_URL)
    if status is None:
        return url
    return f'{url}?{STATUS_PARAM}={status}'


def posts_all_link(request: HttpRequest) -> str:
    return _posts_url()


def posts_published_link(request: HttpRequest) -> str:
    return _posts_url(Post.Status.PUBLISHED)


def posts_drafts_link(request: HttpRequest) -> str:
    return _posts_url(Post.Status.DRAFT)


def posts_all_active(request: HttpRequest) -> bool:
    return STATUS_PARAM not in request.GET


def posts_published_active(request: HttpRequest) -> bool:
    return request.GET.get(STATUS_PARAM) == Post.Status.PUBLISHED


def posts_drafts_active(request: HttpRequest) -> bool:
    return request.GET.get(STATUS_PARAM) == Post.Status.DRAFT


# --- Dashboard ---------------------------------------------------------------


def _percent(part: int, total: int) -> int:
    return round(part * PERCENT / total) if total else 0


def dashboard_callback(
    request: HttpRequest,
    context: dict[str, Any],
) -> dict[str, Any]:
    posts = Post.objects.aggregate(
        published=Count('id', filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count('id', filter=Q(status=Post.Status.DRAFT)),
        uncategorized=Count('id', filter=Q(category__isnull=True)),
    )
    published = posts['published']
    drafts = posts['drafts']
    total_posts = published + drafts

    categories = Category.objects.annotate(total=Count('posts')).order_by(
        '-total',
        'name',
    )
    labels = [category.name for category in categories]
    values = [category.total for category in categories]
    if posts['uncategorized']:
        labels.append(NO_CATEGORY_LABEL)
        values.append(posts['uncategorized'])

    top_authors = (
        User.objects.annotate(total=Count('posts'))
        .filter(total__gt=0)
        .order_by('-total', 'email')[:TOP_AUTHORS_LIMIT]
    )

    context.update(
        {
            'cards': [
                {
                    'title': 'Total users',
                    'value': User.objects.count(),
                    'icon': 'group',
                },
                {
                    'title': 'Published posts',
                    'value': published,
                    'icon': 'task_alt',
                },
                {
                    'title': 'Drafts',
                    'value': drafts,
                    'icon': 'edit_note',
                },
                {
                    'title': 'Comments',
                    'value': Comment.objects.count(),
                    'icon': 'forum',
                },
            ],
            'category_chart': json.dumps(
                {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': CHART_DATASET_LABEL,
                            'data': values,
                            'backgroundColor': CHART_COLOR,
                        },
                    ],
                },
            ),
            'top_authors': {
                'headers': ['#', 'Author', 'Email', 'Posts'],
                'rows': [
                    [
                        position,
                        f'{author.first_name} {author.last_name}',
                        author.email,
                        author.total,
                    ]
                    for position, author in enumerate(top_authors, start=1)
                ],
            },
            'status_progress': [
                {
                    'title': 'Published',
                    'description': f'{published} posts',
                    'value': _percent(published, total_posts),
                },
                {
                    'title': 'Drafts',
                    'description': f'{drafts} posts',
                    'value': _percent(drafts, total_posts),
                },
            ],
        },
    )
    return context
