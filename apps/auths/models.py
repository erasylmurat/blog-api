from typing import Any, ClassVar

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models

NAME_MAX_LENGTH = 50
FIELD_IS_STAFF = 'is_staff'
FIELD_IS_SUPERUSER = 'is_superuser'
ERROR_EMAIL_REQUIRED = 'The Email field must be set.'
ERROR_SUPERUSER_STAFF = 'Superuser must have is_staff=True.'
ERROR_SUPERUSER_FLAG = 'Superuser must have is_superuser=True.'


class UserManager(BaseUserManager['User']):
    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> 'User':
        if not email:
            raise ValueError(ERROR_EMAIL_REQUIRED)
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> 'User':
        extra_fields.setdefault(FIELD_IS_STAFF, True)
        extra_fields.setdefault(FIELD_IS_SUPERUSER, True)

        if extra_fields.get(FIELD_IS_STAFF) is not True:
            raise ValueError(ERROR_SUPERUSER_STAFF)
        if extra_fields.get(FIELD_IS_SUPERUSER) is not True:
            raise ValueError(ERROR_SUPERUSER_FLAG)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=NAME_MAX_LENGTH)
    last_name = models.CharField(max_length=NAME_MAX_LENGTH)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: ClassVar[list[str]] = ['first_name', 'last_name']

    def __str__(self) -> str:
        return self.email
