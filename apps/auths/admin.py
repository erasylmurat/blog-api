from typing import ClassVar

from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter
from unfold.decorators import action, display
from unfold.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, QuerySet
from django.http import HttpRequest

from apps.auths.models import User

ACTIVE_LABELS = {'active': 'success', 'inactive': 'danger'}
STAFF_LABELS = {'staff': 'info'}
TAB = ['tab']


class BlogUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')


class BlogUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = BlogUserChangeForm
    add_form = BlogUserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = (
        'display_header',
        'display_active',
        'display_staff',
        'posts_count',
    )
    list_filter = (
        ('is_active', BooleanRadioFilter),
        ('is_staff', BooleanRadioFilter),
    )
    list_filter_submit = True
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    readonly_fields = ('last_login',)
    actions: ClassVar[list[str]] = ['activate_users', 'deactivate_users']

    fieldsets = (
        (
            'Personal info',
            {
                'classes': TAB,
                'fields': ('email', 'password', 'first_name', 'last_name'),
            },
        ),
        (
            'Permissions',
            {
                'classes': TAB,
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
        (
            'Important dates',
            {
                'classes': TAB,
                'fields': ('last_login',),
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'first_name',
                    'last_name',
                    'password1',
                    'password2',
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        return (
            super()
            .get_queryset(request)
            .annotate(
                posts_total=Count('posts'),
            )
        )

    @display(description='User', header=True, ordering='email')
    def display_header(self, obj: User) -> list[str]:
        initials = f'{obj.first_name[:1]}{obj.last_name[:1]}'.upper()
        full_name = f'{obj.first_name} {obj.last_name}'.strip()
        return [full_name or obj.email, obj.email, initials]

    @display(description='Active', label=ACTIVE_LABELS, ordering='is_active')
    def display_active(self, obj: User) -> tuple[str, str]:
        if obj.is_active:
            return 'active', 'Active'
        return 'inactive', 'Inactive'

    @display(description='Staff', label=STAFF_LABELS, ordering='is_staff')
    def display_staff(self, obj: User) -> tuple[str, str]:
        if obj.is_staff:
            return 'staff', 'Staff'
        return 'regular', 'Regular'

    @display(description='Posts', ordering='posts_total')
    def posts_count(self, obj: User) -> int:
        return obj.posts_total

    @action(description='Activate selected users', icon='check_circle')
    def activate_users(
        self,
        request: HttpRequest,
        queryset: QuerySet[User],
    ) -> None:
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) activated.')

    @action(description='Deactivate selected users', icon='block')
    def deactivate_users(
        self,
        request: HttpRequest,
        queryset: QuerySet[User],
    ) -> None:
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) deactivated.')


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
