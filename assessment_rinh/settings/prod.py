from .base import *  # noqa: F401,F403


SECRET_KEY = env_value('DJANGO_SECRET_KEY', required=True)
DEBUG = False
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', required=True)

# HTTPS
SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = env_bool('DJANGO_SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env_bool('DJANGO_CSRF_COOKIE_SECURE', default=True)
SECURE_HSTS_SECONDS = env_int('DJANGO_SECURE_HSTS_SECONDS', default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', default=True)

# Дополнительные security-заголовки.
# X-Content-Type-Options: nosniff — браузер не «угадывает» MIME, защита от MIME-confusion.
SECURE_CONTENT_TYPE_NOSNIFF = True
# Referrer-Policy: same-origin — внешние ссылки не получат ваш URL целиком.
SECURE_REFERRER_POLICY = 'same-origin'
# Если за reverse-proxy (nginx/traefik), доверяем только X-Forwarded-Proto=https.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookies — недоступны JS, защита от XSS-кражи сессии/CSRF.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Clickjacking — запрещаем фреймить весь сайт.
X_FRAME_OPTIONS = 'DENY'
