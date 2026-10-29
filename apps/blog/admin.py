from typing import Any, ClassVar

from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display
from unfold.sections import TableSection

from django.contrib import admin
from django.db import models
from django.db.models import Count, Prefetch, QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.text import Truncator

from apps.blog.models import Category, Comment, Post, Tag

COMMENT_PREVIEW_LENGTH = 60
SECTION_PREVIEW_LENGTH = 80
SECTION_HEIGHT = 300
INLINE_COMMENTS_PER_PAGE = 10

STATUS_LABELS = {
    Post.Status.PUBLISHED: 'success',
    Post.Status.DRAFT: 'warning',
}
TAB = ['tab']

POST_CHANGELIST_URL = 'admin:blog_post_changelist'
COMMENT_CHANGELIST_URL = 'admin:blog_comment_changelist'
TAG_CHANGE_URL = 'admin:blog_tag_change'
COMMENTS_BY_POST_PARAM = 'post__id__exact'


def _truncate(text: str, length: int) -> str:
    return Truncator(text).chars(length)


# --- Expandable rows (list_sections) ----------------------------------------


class CategoryPostsSection(TableSection):
    verbose_name = 'Posts in this category'
    related_name = 'posts'
    fields: ClassVar[list[str]] = ['title', 'author', 'status', 'created_at']
    height = SECTION_HEIGHT


class PostCommentsSection(TableSection):
    verbose_name = 'Comments'
    related_name = 'comments'
    fields: ClassVar[list[str]] = ['author', 'short_body', 'created_at']
    height = SECTION_HEIGHT

    def short_body(self, instance: Comment) -> str:
        return _truncate(instance.body, SECTION_PREVIEW_LENGTH)

    short_body.short_description = 'Comment'


# --- Category & Tag ----------------------------------------------------------


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'posts_count')
    search_fields = ('name',)
    ordering = ('name',)
    prepopulated_fields: ClassVar[dict[str, tuple[str, ...]]] = {
        'slug': ('name',),
    }
    list_sections = (CategoryPostsSection,)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Category]:
        posts = Post.objects.select_related('author').order_by('-created_at')
        return (
            super()
            .get_queryset(request)
            .annotate(posts_total=Count('posts'))
            .prefetch_related(Prefetch('posts', queryset=posts))
        )

    @display(description='Posts', ordering='posts_total')
    def posts_count(self, obj: Category) -> int:
        return obj.posts_total


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'posts_count')
    search_fields = ('name',)
    ordering = ('name',)
    prepopulated_fields: ClassVar[dict[str, tuple[str, ...]]] = {
        'slug': ('name',),
    }

    def get_queryset(self, request: HttpRequest) -> QuerySet[Tag]:
        return (
            super().get_queryset(request).annotate(posts_total=Count('posts'))
        )

    @display(description='Posts', ordering='posts_total')
    def posts_count(self, obj: Tag) -> int:
        return obj.posts_total


# --- Comment -----------------------------------------------------------------


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ('post_title', 'author', 'short_body', 'created_at')
    list_select_related = ('post', 'author')
    list_filter = (
        ('post', AutocompleteSelectFilter),
        ('author', AutocompleteSelectFilter),
        ('created_at', RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ('body', 'author__email', 'post__title')
    autocomplete_fields = ('post', 'author')
    readonly_fields = ('created_at',)

    @display(description='Post', ordering='post__title')
    def post_title(self, obj: Comment) -> str:
        return obj.post.title

    @display(description='Comment')
    def short_body(self, obj: Comment) -> str:
        return _truncate(obj.body, COMMENT_PREVIEW_LENGTH)


# --- Post --------------------------------------------------------------------


class CommentInline(TabularInline):
    model = Comment
    fields = ('author', 'body', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('author',)
    extra = 0
    tab = True
    per_page = INLINE_COMMENTS_PER_PAGE

    def get_queryset(self, request: HttpRequest) -> QuerySet[Comment]:
        return (
            super()
            .get_queryset(request)
            .select_related('author')
            .order_by('-created_at')
        )


@admin.register(Post)
class PostAdmin(ModelAdmin):
    # list page
    list_display = (
        'display_header',
        'status_label',
        'category',
        'display_tags',
        'comments_count',
        'created_at',
    )
    list_filter = (
        ('status', ChoicesDropdownFilter),
        ('category', RelatedDropdownFilter),
        ('tags', MultipleRelatedDropdownFilter),
        ('author', AutocompleteSelectFilter),
        ('created_at', RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ('title', 'body', 'author__email')
    list_sections = (PostCommentsSection,)

    # actions
    actions: ClassVar[list[str]] = ['publish_selected', 'move_to_drafts']
    actions_row = ('publish_row', 'unpublish_row')
    actions_list = ('publish_all_drafts',)
    actions_detail = ('open_comments',)
    actions_submit_line = ('save_and_publish',)

    # edit page
    fieldsets = (
        ('Content', {'classes': TAB, 'fields': ('title', 'slug', 'body')}),
        (
            'Classification',
            {'classes': TAB, 'fields': ('category', 'tags', 'status')},
        ),
        (
            'Meta',
            {
                'classes': TAB,
                'fields': ('author', 'created_at', 'updated_at'),
            },
        ),
    )
    prepopulated_fields: ClassVar[dict[str, tuple[str, ...]]] = {
        'slug': ('title',),
    }
    autocomplete_fields = ('author', 'category', 'tags')
    readonly_fields = ('created_at', 'updated_at')
    formfield_overrides: ClassVar[dict[type, dict[str, Any]]] = {
        models.TextField: {'widget': WysiwygWidget},
    }
    inlines = (CommentInline,)
    warn_unsaved_form = True

    def get_queryset(self, request: HttpRequest) -> QuerySet[Post]:
        comments = Comment.objects.select_related('author').order_by(
            '-created_at',
        )
        return (
            super()
            .get_queryset(request)
            .select_related('author', 'category')
            .prefetch_related(
                'tags',
                Prefetch('comments', queryset=comments),
            )
            .annotate(comments_total=Count('comments', distinct=True))
        )

    # --- columns ---

    @display(description='Post', header=True, ordering='title')
    def display_header(self, obj: Post) -> list[str]:
        return [obj.title, obj.author.email]

    @display(description='Status', label=STATUS_LABELS, ordering='status')
    def status_label(self, obj: Post) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description='Tags', dropdown=True)
    def display_tags(self, obj: Post) -> dict[str, Any]:
        tags = obj.tags.all()  # uses prefetch_related, no extra query
        return {
            'title': f'{len(tags)} tags',
            'items': [
                {
                    'title': tag.name,
                    'link': reverse(TAG_CHANGE_URL, args=(tag.pk,)),
                }
                for tag in tags
            ],
        }

    @display(description='Comments', ordering='comments_total')
    def comments_count(self, obj: Post) -> int:
        return obj.comments_total

    # --- bulk actions (checkboxes) ---

    @action(description='Publish selected', icon='publish')
    def publish_selected(
        self,
        request: HttpRequest,
        queryset: QuerySet[Post],
    ) -> None:
        updated = queryset.update(status=Post.Status.PUBLISHED)
        self.message_user(request, f'{updated} post(s) published.')

    @action(description='Move to drafts', icon='unpublished')
    def move_to_drafts(
        self,
        request: HttpRequest,
        queryset: QuerySet[Post],
    ) -> None:
        updated = queryset.update(status=Post.Status.DRAFT)
        self.message_user(request, f'{updated} post(s) moved to drafts.')

    # --- row actions ---

    def _set_status(
        self,
        request: HttpRequest,
        object_id: int,
        status: str,
    ) -> HttpResponseRedirect:
        post = get_object_or_404(Post, pk=object_id)
        post.status = status
        post.save(update_fields=['status', 'updated_at'])
        self.message_user(
            request,
            f'"{post.title}" is now {post.get_status_display().lower()}.',
        )
        return HttpResponseRedirect(
            request.headers.get('referer') or reverse(POST_CHANGELIST_URL),
        )

    @action(description='Publish', icon='publish')
    def publish_row(
        self,
        request: HttpRequest,
        object_id: int,
    ) -> HttpResponseRedirect:
        return self._set_status(request, object_id, Post.Status.PUBLISHED)

    @action(description='Unpublish', icon='unpublished')
    def unpublish_row(
        self,
        request: HttpRequest,
        object_id: int,
    ) -> HttpResponseRedirect:
        return self._set_status(request, object_id, Post.Status.DRAFT)

    # --- list action (above the table) ---

    @action(description='Publish all drafts', icon='done_all')
    def publish_all_drafts(self, request: HttpRequest) -> HttpResponseRedirect:
        updated = Post.objects.filter(status=Post.Status.DRAFT).update(
            status=Post.Status.PUBLISHED,
        )
        self.message_user(request, f'{updated} draft(s) published.')
        return HttpResponseRedirect(reverse(POST_CHANGELIST_URL))

    # --- detail action (post page) ---

    @action(description='Open comments', icon='forum')
    def open_comments(
        self,
        request: HttpRequest,
        object_id: int,
    ) -> HttpResponseRedirect:
        url = reverse(COMMENT_CHANGELIST_URL)
        return HttpResponseRedirect(
            f'{url}?{COMMENTS_BY_POST_PARAM}={object_id}',
        )

    # --- submit line action (next to Save) ---

    @action(description='Save & publish')
    def save_and_publish(self, request: HttpRequest, obj: Post) -> None:
        obj.status = Post.Status.PUBLISHED
        obj.save(update_fields=['status', 'updated_at'])
        self.message_user(request, f'"{obj.title}" saved and published.')
