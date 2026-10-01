from decouple import AutoConfig

config = AutoConfig(search_path="settings")

SECRET_KEY: str = config("BLOG_SECRET_KEY", default="unsafe_secret_key")
DEBUG: bool = config("BLOG_DEBUG", default=True, cast=bool)
ENV_ID: str = config("BLOG_ENV_ID", default="local")
