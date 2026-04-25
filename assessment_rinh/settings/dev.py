from .base import *  # noqa: F401,F403


DEBUG = env_bool('DJANGO_DEBUG', default=True)
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', default='localhost,127.0.0.1,[::1]')
