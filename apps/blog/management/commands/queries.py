from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import (
    BaseCommand,
    CommandError,
    CommandParser,
)
from django.db import connection
from django.db.models import Count, Model, QuerySet
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.blog import queries
from apps.blog.models import Post

User = get_user_model()

ROWS_TO_SHOW = 5
INDENT = '  '
CHANGING_QUERIES = range(40, 45)  # 40–44 change the data
BETWEEN_DAYS = 30
FULL_NAME_PREFIX_LENGTH = 3
MIN_TAGS_FOR_PAIR = 2

ERROR_UNKNOWN_NUMBER = 'Query #{number} does not exist. Use 1–{last}.'


# --- Sample arguments --------------------------------------------------------
# Values that depend on the data are callables, they are resolved before
# the query runs, so they are not counted.


def _author_email() -> str:
    """Email of the user with the most published posts."""
    user = (
        User.objects.filter(posts__status=Post.Status.PUBLISHED)
        .annotate(total=Count('posts'))
        .order_by('-total')
        .first()
    )
    return user.email if user else ''


def _post_slug() -> str:
    post = Post.objects.order_by('-created_at').first()
    return post.slug if post else ''


def _title_word() -> str:
    post = Post.objects.order_by('-created_at').first()
    return post.title.split()[0] if post else ''


def _full_name_part() -> str:
    user = User.objects.filter(posts__isnull=False).first()
    if not user:
        return ''
    return f'{user.first_name} {user.last_name[:FULL_NAME_PREFIX_LENGTH]}'


def _tag_pair() -> tuple[str, str]:
    post = (
        Post.objects.annotate(tag_total=Count('tags'))
        .filter(tag_total__gte=MIN_TAGS_FOR_PAIR)
        .first()
    )
    if not post:
        return '', ''
    first, second = post.tags.values_list('slug', flat=True)[
        :MIN_TAGS_FOR_PAIR
    ]
    return first, second


QUERY_ARGUMENTS: dict[int, dict[str, Any]] = {
    4: {'slug': _post_slug},
    7: {'page': 2},
    8: {'word': _title_word},
    9: {'domain': 'example.com'},
    11: {'slugs': ['python', 'django', 'devops']},
    12: {
        'year': lambda: timezone.now().year,
        'month': lambda: timezone.now().month,
    },
    13: {'days': 30},
    14: {
        'start': lambda: (
            timezone.now() - timedelta(days=BETWEEN_DAYS)
        ).date(),
        'end': lambda: timezone.now().date(),
    },
    15: {'email': lambda: _author_email().upper()},
    16: {'tag_slug': 'docker'},
    17: {'category_slug': 'python'},
    21: {
        'first_slug': lambda: _tag_pair()[0],
        'second_slug': lambda: _tag_pair()[1],
    },
    22: {'text': _title_word},
    34: {'min_posts': 10},
    37: {'text': _full_name_part},
    40: {'name': 'Django ORM'},
    41: {'days': 30},
    42: {'category_slug': 'python', 'tag_slug': 'docker'},
    43: {'source_slug': 'career', 'target_slug': 'django'},
}


def _resolve(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        name: value() if callable(value) else value
        for name, value in arguments.items()
    }


class Command(BaseCommand):
    help = 'Run the Homework 3 ORM queries and show results and SQL counts.'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--number',
            type=int,
            help='Run only this query (40–44 change the data)',
        )
        parser.add_argument(
            '--sql',
            action='store_true',
            help='Also print the SQL sent to the database',
        )

    def handle(self, *args: Any, **options: Any) -> None:
        number: int | None = options['number']
        show_sql: bool = options['sql']

        if number is None:
            numbers = [n for n in queries.QUERIES if n not in CHANGING_QUERIES]
        elif number in queries.QUERIES:
            numbers = [number]
        else:
            raise CommandError(
                ERROR_UNKNOWN_NUMBER.format(
                    number=number,
                    last=max(queries.QUERIES),
                ),
            )

        for query_number in numbers:
            self._run(query_number, show_sql)

    def _run(self, number: int, show_sql: bool) -> None:
        function: Callable[..., Any] = queries.QUERIES[number]
        arguments = _resolve(QUERY_ARGUMENTS.get(number, {}))

        with CaptureQueriesContext(connection) as context:
            result = function(**arguments)
            rows = self._evaluate(result)

        count = len(context.captured_queries)
        word = 'query' if count == 1 else 'queries'
        self.stdout.write(
            self.style.SUCCESS(
                f'#{number} {function.__name__} — {count} SQL {word}',
            ),
        )
        if show_sql:
            for captured in context.captured_queries:
                self.stdout.write(captured['sql'])

        self._print_result(result, rows)
        self.stdout.write('')

    @staticmethod
    def _evaluate(result: Any) -> list[Any] | None:
        """Make a lazy QuerySet run inside the capture block."""
        if isinstance(result, QuerySet):
            return list(result)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and all(
            isinstance(value, list) for value in result.values()
        ):
            return list(result.items())
        return None

    def _print_result(self, result: Any, rows: list[Any] | None) -> None:
        if rows is None:
            self.stdout.write(f'{INDENT}{self._format(result, [])}')
            return

        annotations = (
            list(result.query.annotations)
            if isinstance(result, QuerySet)
            else []
        )
        for row in rows[:ROWS_TO_SHOW]:
            self.stdout.write(f'{INDENT}{self._format(row, annotations)}')
        self.stdout.write(f'{INDENT}({len(rows)} rows)')

    @staticmethod
    def _format(value: Any, annotations: list[str]) -> str:
        if isinstance(value, Model):
            if not annotations:
                return str(value)
            extra = {name: getattr(value, name) for name in annotations}
            return f'{value} {extra}'
        if isinstance(value, tuple) and value and isinstance(value[0], Model):
            return f'{value[0]}, {value[1]}'
        return str(value)
