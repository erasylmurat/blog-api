"""Homework 3: 50 Django ORM queries over the blog data."""

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import (
    Avg,
    Case,
    CharField,
    Count,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, TruncMonth
from django.utils import timezone
from django.utils.text import slugify

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()

NEWEST_POSTS_LIMIT = 5
POSTS_PER_PAGE = 10
TOP_AUTHORS_LIMIT = 5
EDIT_THRESHOLD = timedelta(hours=1)
UNCATEGORIZED = 'Uncategorized'
AVERAGE_PRECISION = 2

HOT_MIN_COMMENTS = 10
NORMAL_MIN_COMMENTS = 3
POPULARITY_HOT = 'hot'
POPULARITY_NORMAL = 'normal'
POPULARITY_QUIET = 'quiet'

FEED_LIMIT = 50
NEWEST_WITH_TAGS_LIMIT = 20
FEED_SEPARATOR = ' | '
TAGS_SEPARATOR = ', '

PUBLISHED = Post.Status.PUBLISHED
DRAFT = Post.Status.DRAFT


# --- Level 1 — First queries -------------------------------------------------


def categories_by_name() -> QuerySet[Category]:
    """All categories, sorted by name A → Z."""
    return Category.objects.order_by('name')


def published_posts() -> QuerySet[Post]:
    """Published posts, newest first."""
    return Post.objects.filter(status=PUBLISHED).order_by('-created_at')


def newest_published_posts() -> QuerySet[Post]:
    """The 5 newest published posts."""
    return published_posts()[:NEWEST_POSTS_LIMIT]


def post_by_slug(slug: str) -> Post | None:
    """The post with this slug, or None."""
    return Post.objects.filter(slug=slug).first()


def active_users_count() -> int:
    """Number of active users, staff users are not counted."""
    return User.objects.filter(is_active=True, is_staff=False).count()


def has_drafts() -> bool:
    """True if there is at least one draft post."""
    return Post.objects.filter(status=DRAFT).exists()


def published_posts_page(page: int) -> QuerySet[Post]:
    """One page (10 posts) of published posts, newest first."""
    start = (page - 1) * POSTS_PER_PAGE
    return published_posts()[start : start + POSTS_PER_PAGE]


# --- Level 2 — Field lookups -------------------------------------------------


def posts_with_word_in_title(word: str) -> QuerySet[Post]:
    """Posts whose title contains the word, case-insensitive."""
    return Post.objects.filter(title__icontains=word)


def users_with_email_domain(domain: str) -> QuerySet[User]:
    """Users whose email ends with @domain."""
    return User.objects.filter(email__iendswith=f'@{domain}')


def posts_without_category() -> QuerySet[Post]:
    """Posts that have no category."""
    return Post.objects.filter(category__isnull=True)


def categories_by_slugs(slugs: list[str]) -> QuerySet[Category]:
    """Categories whose slug is in the list."""
    return Category.objects.filter(slug__in=slugs)


def posts_in_month(year: int, month: int) -> QuerySet[Post]:
    """Posts created in this month of this year."""
    return Post.objects.filter(
        created_at__year=year,
        created_at__month=month,
    )


def posts_last_days(days: int) -> QuerySet[Post]:
    """Posts created in the last `days` days."""
    since = timezone.now() - timedelta(days=days)
    return Post.objects.filter(created_at__gte=since)


def posts_between(start: date, end: date) -> QuerySet[Post]:
    """Posts created from start to end, both days included."""
    return Post.objects.filter(created_at__date__range=(start, end))


# --- Level 3 — Queries across relations --------------------------------------


def author_published_posts(email: str) -> QuerySet[Post]:
    """Published posts of the author with this email (case-insensitive)."""
    return Post.objects.filter(status=PUBLISHED, author__email__iexact=email)


def posts_with_tag(tag_slug: str) -> QuerySet[Post]:
    """Posts that have the tag with this slug."""
    return Post.objects.filter(tags__slug=tag_slug)


def comments_in_category(category_slug: str) -> QuerySet[Comment]:
    """Comments on posts of the category with this slug."""
    return Comment.objects.filter(post__category__slug=category_slug)


def users_with_published_posts() -> QuerySet[User]:
    """Users with at least one published post, each user once."""
    return User.objects.filter(posts__status=PUBLISHED).distinct()


def posts_without_tags() -> QuerySet[Post]:
    """Posts that have no tags."""
    return Post.objects.filter(tags__isnull=True)


def users_without_comments() -> QuerySet[User]:
    """Users who have never written a comment."""
    return User.objects.filter(comments__isnull=True)


def posts_with_both_tags(first_slug: str, second_slug: str) -> QuerySet[Post]:
    """Posts that have both tags (two filter() calls = two JOINs)."""
    return Post.objects.filter(tags__slug=first_slug).filter(
        tags__slug=second_slug,
    )


# --- Level 4 — Q and F -------------------------------------------------------


def search_posts(text: str) -> QuerySet[Post]:
    """Posts with the text in the title or in the body."""
    return Post.objects.filter(
        Q(title__icontains=text) | Q(body__icontains=text),
    )


def published_posts_missing_info() -> QuerySet[Post]:
    """Published posts without a category or without tags, each once."""
    return (
        Post.objects.filter(status=PUBLISHED)
        .filter(Q(category__isnull=True) | Q(tags__isnull=True))
        .distinct()
    )


def edited_posts() -> QuerySet[Post]:
    """Posts edited more than 1 hour after they were created."""
    return Post.objects.filter(
        updated_at__gt=F('created_at') + EDIT_THRESHOLD,
    )


def comments_by_post_author() -> QuerySet[Comment]:
    """Comments written by the author of the post under their own post."""
    return Comment.objects.filter(author=F('post__author'))


def comments_before_post() -> QuerySet[Comment]:
    """Comments created before their post (must be empty)."""
    return Comment.objects.filter(created_at__lt=F('post__created_at'))


# --- Level 5 — values and values_list ----------------------------------------


def published_authors_emails() -> list[str]:
    """Unique emails of authors with published posts, sorted A → Z."""
    return list(
        User.objects.filter(posts__status=PUBLISHED)
        .order_by('email')
        .values_list('email', flat=True)
        .distinct(),
    )


def published_posts_overview() -> list[dict[str, Any]]:
    """title, author_email, category_name for every published post."""
    return list(
        Post.objects.filter(status=PUBLISHED).values(
            'title',
            author_email=F('author__email'),
            category_name=Coalesce(
                F('category__name'),
                Value(UNCATEGORIZED),
            ),
        ),
    )


# --- Level 6 — aggregate -----------------------------------------------------


def posts_stats() -> dict[str, Any]:
    """Totals and first/last post dates in one SQL query."""
    return Post.objects.aggregate(
        total=Count('id'),
        published=Count('id', filter=Q(status=PUBLISHED)),
        drafts=Count('id', filter=Q(status=DRAFT)),
        first_post_at=Min('created_at'),
        last_post_at=Max('created_at'),
    )


def average_comments_per_post() -> float:
    """Average number of comments on a published post, 2 digits."""
    result = (
        Post.objects.filter(status=PUBLISHED)
        .annotate(comment_count=Count('comments'))
        .aggregate(average=Avg('comment_count', default=0.0))
    )
    return round(float(result['average']), AVERAGE_PRECISION)


# --- Level 7 — annotate ------------------------------------------------------


def categories_with_post_count() -> QuerySet[Category]:
    """Every category with post_count, most posts first, then by name."""
    return Category.objects.annotate(post_count=Count('posts')).order_by(
        '-post_count',
        'name',
    )


def categories_with_published_count() -> QuerySet[Category]:
    """Every category with published_count (0 included)."""
    return Category.objects.annotate(
        published_count=Count('posts', filter=Q(posts__status=PUBLISHED)),
    ).order_by('name')


def top_authors() -> QuerySet[User]:
    """Top 5 users by number of published posts."""
    return User.objects.annotate(
        published_count=Count('posts', filter=Q(posts__status=PUBLISHED)),
    ).order_by('-published_count', 'email')[:TOP_AUTHORS_LIMIT]


def popular_tags(min_posts: int) -> QuerySet[Tag]:
    """Tags used in at least min_posts posts, with post_count."""
    return (
        Tag.objects.annotate(post_count=Count('posts'))
        .filter(post_count__gte=min_posts)
        .order_by('-post_count', 'name')
    )


def posts_per_status() -> list[dict[str, Any]]:
    """Number of posts for each status."""
    return list(
        Post.objects.values('status')
        .annotate(count=Count('id'))
        .order_by('status'),
    )


def users_activity() -> QuerySet[User]:
    """Every user with correct post_count and comment_count."""
    return User.objects.annotate(
        post_count=Count('posts', distinct=True),
        comment_count=Count('comments', distinct=True),
    ).order_by('email')


# --- Level 8 — Database functions and conditions -----------------------------


def search_users_by_full_name(text: str) -> QuerySet[User]:
    """Users whose full name "First Last" contains the text."""
    return User.objects.annotate(
        full_name=Concat(
            'first_name',
            Value(' '),
            'last_name',
            output_field=CharField(),
        ),
    ).filter(full_name__icontains=text)


def published_posts_per_month() -> list[dict[str, Any]]:
    """Number of published posts in each month, oldest month first."""
    return list(
        Post.objects.filter(status=PUBLISHED)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month'),
    )


def posts_with_popularity() -> QuerySet[Post]:
    """Every post with comment_count and popularity (hot/normal/quiet)."""
    return Post.objects.annotate(
        comment_count=Count('comments'),
        popularity=Case(
            When(
                comment_count__gte=HOT_MIN_COMMENTS, then=Value(POPULARITY_HOT)
            ),
            When(
                comment_count__gte=NORMAL_MIN_COMMENTS,
                then=Value(POPULARITY_NORMAL),
            ),
            default=Value(POPULARITY_QUIET),
            output_field=CharField(),
        ),
    ).order_by('-comment_count')


# --- Level 9 — Changing data -------------------------------------------------


def get_or_create_tag(name: str) -> tuple[Tag, bool]:
    """Return the tag with this name, create it if it does not exist."""
    return Tag.objects.get_or_create(
        slug=slugify(name),
        defaults={'name': name},
    )


def publish_old_drafts(days: int) -> int:
    """Publish drafts older than `days` days in one SQL query."""
    now = timezone.now()
    return Post.objects.filter(
        status=DRAFT,
        created_at__lt=now - timedelta(days=days),
    ).update(status=PUBLISHED, updated_at=now)


def tag_category_posts(category_slug: str, tag_slug: str) -> int:
    """Add the tag to every post of the category (no duplicates)."""
    tag = Tag.objects.get(slug=tag_slug)
    posts = Post.objects.filter(category__slug=category_slug)
    tag.posts.add(*posts)  # add() skips posts that already have the tag
    return posts.count()


def merge_categories(source_slug: str, target_slug: str) -> int:
    """Move all posts from source to target, then delete source."""
    target = Category.objects.get(slug=target_slug)
    moved = Post.objects.filter(category__slug=source_slug).update(
        category=target,
    )
    Category.objects.filter(slug=source_slug).delete()
    return moved


def delete_inactive_users_comments() -> int:
    """Delete all comments written by inactive users."""
    deleted, _ = Comment.objects.filter(author__is_active=False).delete()
    return deleted


# --- Level 10 — select_related and prefetch_related --------------------------


def published_feed() -> list[str]:
    """50 newest published posts as "title | email | category" (1 query)."""
    posts = published_posts().select_related('author', 'category')[:FEED_LIMIT]
    return [
        FEED_SEPARATOR.join(
            (
                post.title,
                post.author.email,
                post.category.name if post.category else UNCATEGORIZED,
            ),
        )
        for post in posts
    ]


def newest_posts_with_tags() -> list[str]:
    """20 newest posts as "title: tag1, tag2" (at most 2 queries)."""
    posts = Post.objects.order_by('-created_at').prefetch_related(
        Prefetch('tags', queryset=Tag.objects.order_by('name')),
    )[:NEWEST_WITH_TAGS_LIMIT]
    return [
        f'{post.title}: '
        f'{TAGS_SEPARATOR.join(tag.name for tag in post.tags.all())}'
        for post in posts
    ]


def categories_with_published_posts() -> dict[str, list[str]]:
    """{category: [published titles, newest first]} (at most 2 queries)."""
    categories = Category.objects.order_by('name').prefetch_related(
        Prefetch(
            'posts',
            queryset=published_posts(),
            to_attr='published_posts',
        ),
    )
    return {
        category.name: [post.title for post in category.published_posts]
        for category in categories
    }


# --- Level 11 — Subquery and Exists ------------------------------------------


def posts_with_last_comment() -> QuerySet[Post]:
    """Published posts with last_comment: body of the newest comment."""
    newest_comment = Comment.objects.filter(post=OuterRef('pk')).order_by(
        '-created_at',
    )
    return published_posts().annotate(
        last_comment=Subquery(newest_comment.values('body')[:1]),
    )


def posts_with_staff_comments() -> QuerySet[Post]:
    """Posts with at least one comment from a staff user (Exists)."""
    staff_comments = Comment.objects.filter(
        post=OuterRef('pk'),
        author__is_staff=True,
    )
    return Post.objects.filter(Exists(staff_comments))


def users_with_draft_as_latest_post() -> QuerySet[User]:
    """Users whose newest post is a draft, with latest_post_status."""
    newest_post = Post.objects.filter(author=OuterRef('pk')).order_by(
        '-created_at',
    )
    return User.objects.annotate(
        latest_post_status=Subquery(newest_post.values('status')[:1]),
    ).filter(latest_post_status=DRAFT)


QUERIES: dict[int, Callable[..., Any]] = {
    1: categories_by_name,
    2: published_posts,
    3: newest_published_posts,
    4: post_by_slug,
    5: active_users_count,
    6: has_drafts,
    7: published_posts_page,
    8: posts_with_word_in_title,
    9: users_with_email_domain,
    10: posts_without_category,
    11: categories_by_slugs,
    12: posts_in_month,
    13: posts_last_days,
    14: posts_between,
    15: author_published_posts,
    16: posts_with_tag,
    17: comments_in_category,
    18: users_with_published_posts,
    19: posts_without_tags,
    20: users_without_comments,
    21: posts_with_both_tags,
    22: search_posts,
    23: published_posts_missing_info,
    24: edited_posts,
    25: comments_by_post_author,
    26: comments_before_post,
    27: published_authors_emails,
    28: published_posts_overview,
    29: posts_stats,
    30: average_comments_per_post,
    31: categories_with_post_count,
    32: categories_with_published_count,
    33: top_authors,
    34: popular_tags,
    35: posts_per_status,
    36: users_activity,
    37: search_users_by_full_name,
    38: published_posts_per_month,
    39: posts_with_popularity,
    40: get_or_create_tag,
    41: publish_old_drafts,
    42: tag_category_posts,
    43: merge_categories,
    44: delete_inactive_users_comments,
    45: published_feed,
    46: newest_posts_with_tags,
    47: categories_with_published_posts,
    48: posts_with_last_comment,
    49: posts_with_staff_comments,
    50: users_with_draft_as_latest_post,
}
