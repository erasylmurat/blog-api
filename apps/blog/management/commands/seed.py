import random
import time
from datetime import datetime, timedelta
from typing import Any

from faker import Faker

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import (
    BaseCommand,
    CommandError,
    CommandParser,
)
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()

DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500

SEED_PASSWORD = 'seedpass123'
EMAIL_DOMAIN = 'example.com'

INACTIVE_USERS_RATIO = 0.1
STAFF_USERS_RATIO = 0.1
PUBLISHED_POSTS_RATIO = 0.7
POSTS_WITHOUT_CATEGORY_RATIO = 0.1

MIN_TAGS_PER_POST = 0
MAX_TAGS_PER_POST = 5
MIN_PARAGRAPHS = 3
MAX_PARAGRAPHS = 6
MIN_TITLE_WORDS = 3
MAX_TITLE_WORDS = 8
MIN_COMMENT_SENTENCES = 1
MAX_COMMENT_SENTENCES = 3

POSTS_MAX_AGE_DAYS = 365
FIRST_SLUG_SUFFIX = 2
SLUG_SUFFIX_RESERVE = 6
SUMMARY_WIDTH = 15
# body is edited with a WYSIWYG editor, so paragraphs are split with HTML
PARAGRAPH_SEPARATOR = '<br><br>'

CATEGORY_NAMES = [
    'Python',
    'Django',
    'DevOps',
    'Databases',
    'Frontend',
    'Security',
    'Machine Learning',
    'Career',
]

TAG_NAMES = [
    'beginner',
    'advanced',
    'tutorial',
    'tips',
    'best-practices',
    'performance',
    'testing',
    'docker',
    'kubernetes',
    'postgresql',
    'redis',
    'rest-api',
    'drf',
    'celery',
    'async',
    'linux',
    'git',
    'ci-cd',
    'javascript',
    'architecture',
]

ERROR_NEGATIVE = '--{name} must not be negative (got {value}).'
ERROR_NO_USERS = (
    'Cannot create posts or comments: there are no users. '
    'Use --users to create some.'
)
ERROR_NO_PUBLISHED_POSTS = (
    'Cannot create comments: there are no published posts. '
    'Use --posts to create some.'
)


class Command(BaseCommand):
    help = 'Fill the database with fake data.'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--users',
            type=int,
            default=DEFAULT_USERS,
            help='Number of users to create',
        )
        parser.add_argument(
            '--posts',
            type=int,
            default=DEFAULT_POSTS,
            help='Number of posts to create',
        )
        parser.add_argument(
            '--comments',
            type=int,
            default=DEFAULT_COMMENTS,
            help='Number of comments to create',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing data before seeding',
        )

    def handle(self, *args: Any, **options: Any) -> None:
        users_count: int = options['users']
        posts_count: int = options['posts']
        comments_count: int = options['comments']
        clear: bool = options['clear']

        for name, value in (
            ('users', users_count),
            ('posts', posts_count),
            ('comments', comments_count),
        ):
            if value < 0:
                raise CommandError(
                    ERROR_NEGATIVE.format(name=name, value=value)
                )

        self.fake = Faker()
        started = time.perf_counter()

        with transaction.atomic():
            if clear:
                self._clear()

            users = self._create_users(users_count)
            categories = self._create_named(Category, CATEGORY_NAMES)
            tags = self._create_named(Tag, TAG_NAMES)
            posts = self._create_posts(posts_count)
            comments = self._create_comments(comments_count)

        elapsed = time.perf_counter() - started

        if clear:
            self.stdout.write(self.style.WARNING('Existing data deleted.'))
        self._write_line('Users', users)
        self._write_line('Categories', categories)
        self._write_line('Tags', tags)
        self._write_line('Posts', posts)
        self._write_line('Comments', comments)
        self.stdout.write(
            self.style.SUCCESS(f'Done in {elapsed:.2f} seconds'),
        )

    def _write_line(self, label: str, count: int) -> None:
        width = SUMMARY_WIDTH - len(label) - 1
        self.stdout.write(f'{label}:{count:>{width}} created')

    def _clear(self) -> None:
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _create_users(self, count: int) -> int:
        if count == 0:
            return 0

        used_emails = set(
            User.objects.values_list('email', flat=True),
        )
        password = make_password(SEED_PASSWORD)
        users = []

        for _ in range(count):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()
            email = self._unique_email(first_name, last_name, used_emails)
            users.append(
                User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password,
                    is_active=random.random() >= INACTIVE_USERS_RATIO,
                    is_staff=random.random() < STAFF_USERS_RATIO,
                ),
            )

        User.objects.bulk_create(users)
        return len(users)

    @staticmethod
    def _unique_email(
        first_name: str,
        last_name: str,
        used_emails: set[str],
    ) -> str:
        local_part = slugify(f'{first_name}.{last_name}').replace('-', '.')
        email = f'{local_part}@{EMAIL_DOMAIN}'
        suffix = FIRST_SLUG_SUFFIX

        while email in used_emails:
            email = f'{local_part}{suffix}@{EMAIL_DOMAIN}'
            suffix += 1

        used_emails.add(email)
        return email

    @staticmethod
    def _create_named(
        model: type[Category] | type[Tag],
        names: list[str],
    ) -> int:
        existing = set(model.objects.values_list('name', flat=True))
        new_objects = [
            model(name=name, slug=slugify(name))
            for name in names
            if name not in existing
        ]
        model.objects.bulk_create(new_objects)
        return len(new_objects)

    def _create_posts(self, count: int) -> int:
        if count == 0:
            return 0

        author_ids = list(User.objects.values_list('id', flat=True))
        if not author_ids:
            raise CommandError(ERROR_NO_USERS)

        category_ids = list(Category.objects.values_list('id', flat=True))
        tag_ids = list(Tag.objects.values_list('id', flat=True))
        used_slugs = set(Post.objects.values_list('slug', flat=True))
        slug_max_length = Post._meta.get_field('slug').max_length
        title_max_length = Post._meta.get_field('title').max_length

        posts = []
        for _ in range(count):
            title = self._title()[:title_max_length]
            posts.append(
                Post(
                    author_id=random.choice(author_ids),
                    title=title,
                    slug=self._unique_slug(
                        title,
                        used_slugs,
                        slug_max_length,
                    ),
                    body=self._body(),
                    category_id=self._random_category(category_ids),
                    status=(
                        Post.Status.PUBLISHED
                        if random.random() < PUBLISHED_POSTS_RATIO
                        else Post.Status.DRAFT
                    ),
                ),
            )

        Post.objects.bulk_create(posts)

        # created_at uses auto_now_add, so random dates are set afterwards
        now = timezone.now()
        for post in posts:
            post.created_at = self._random_date(now, POSTS_MAX_AGE_DAYS)
            post.updated_at = post.created_at
        Post.objects.bulk_update(posts, ['created_at', 'updated_at'])

        for post in posts:
            tags_number = random.randint(
                MIN_TAGS_PER_POST,
                min(MAX_TAGS_PER_POST, len(tag_ids)),
            )
            post.tags.set(random.sample(tag_ids, tags_number))

        return len(posts)

    def _title(self) -> str:
        words = random.randint(MIN_TITLE_WORDS, MAX_TITLE_WORDS)
        return self.fake.sentence(nb_words=words).rstrip('.')

    def _body(self) -> str:
        paragraphs = self.fake.paragraphs(
            nb=random.randint(MIN_PARAGRAPHS, MAX_PARAGRAPHS),
        )
        return PARAGRAPH_SEPARATOR.join(paragraphs)

    @staticmethod
    def _random_category(category_ids: list[int]) -> int | None:
        if not category_ids:
            return None
        if random.random() < POSTS_WITHOUT_CATEGORY_RATIO:
            return None
        return random.choice(category_ids)

    @staticmethod
    def _unique_slug(
        title: str,
        used_slugs: set[str],
        max_length: int,
    ) -> str:
        base = slugify(title)[: max_length - SLUG_SUFFIX_RESERVE]
        base = base.strip('-')
        slug = base
        suffix = FIRST_SLUG_SUFFIX

        while slug in used_slugs:
            slug = f'{base}-{suffix}'
            suffix += 1

        used_slugs.add(slug)
        return slug

    @staticmethod
    def _random_date(end: datetime, max_age_days: int) -> datetime:
        max_seconds = int(timedelta(days=max_age_days).total_seconds())
        return end - timedelta(seconds=random.randint(0, max_seconds))

    def _create_comments(self, count: int) -> int:
        if count == 0:
            return 0

        author_ids = list(User.objects.values_list('id', flat=True))
        if not author_ids:
            raise CommandError(ERROR_NO_USERS)

        published_posts = list(
            Post.objects.filter(status=Post.Status.PUBLISHED).values_list(
                'id',
                'created_at',
            ),
        )
        if not published_posts:
            raise CommandError(ERROR_NO_PUBLISHED_POSTS)

        comments = []
        dates = []
        now = timezone.now()

        for _ in range(count):
            post_id, post_created_at = random.choice(published_posts)
            sentences = self.fake.sentences(
                nb=random.randint(
                    MIN_COMMENT_SENTENCES,
                    MAX_COMMENT_SENTENCES,
                ),
            )
            comments.append(
                Comment(
                    post_id=post_id,
                    author_id=random.choice(author_ids),
                    body=' '.join(sentences),
                ),
            )
            age_days = max((now - post_created_at).days, 0)
            dates.append(self._random_date(now, age_days))

        Comment.objects.bulk_create(comments)

        for comment, created_at in zip(comments, dates, strict=True):
            comment.created_at = created_at
        Comment.objects.bulk_update(comments, ['created_at'])

        return len(comments)
