import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent.parent


def load_dotenv(path):
    if not path.exists():
        return

    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value


load_dotenv(BASE_DIR / '.env')


def env_value(name, default=None, *, required=False):
    value = os.environ.get(name)
    if value is None or value == '':
        if required:
            raise ImproperlyConfigured(f'Не задана переменная окружения {name}.')
        return default
    return value


def env_bool(name, default=False):
    value = env_value(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_int(name, default=0):
    value = env_value(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(f'Переменная окружения {name} должна быть целым числом.') from exc


def env_list(name, default=None, *, required=False):
    raw_value = env_value(name, default=default, required=required)
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(',') if item.strip()]


SECRET_KEY = env_value(
    'DJANGO_SECRET_KEY',
    default='django-insecure-local-development-key-change-me-before-production',
)

DEBUG = env_bool('DJANGO_DEBUG', default=False)

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', default='localhost,127.0.0.1,[::1]')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
    'teachers.apps.TeachersConfig',
    'programs.apps.ProgramsConfig',
    'competencies.apps.CompetenciesConfig',
    'disciplines.apps.DisciplinesConfig',
    'assessment.apps.AssessmentConfig',
    'reports.apps.ReportsConfig',
    'export.apps.ExportConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'core.middleware.AuthRateLimitMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'assessment_rinh.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.role_flags',
            ],
        },
    },
]

WSGI_APPLICATION = 'assessment_rinh.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': env_value('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': env_value('DB_NAME', default='assessment_rinh'),
        'USER': env_value('DB_USER', default='postgres'),
        'PASSWORD': env_value('DB_PASSWORD', default=''),
        'HOST': env_value('DB_HOST', default='localhost'),
        'PORT': env_value('DB_PORT', default='5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'assessment_workspace'
LOGOUT_REDIRECT_URL = 'home'

CACHES = {
    'default': {
        'BACKEND': env_value(
            'DJANGO_CACHE_BACKEND',
            default='django.core.cache.backends.locmem.LocMemCache',
        ),
        'LOCATION': env_value('DJANGO_CACHE_LOCATION', default='assessment-rinh-default'),
    },
}

HOME_STATS_CACHE_TTL = env_int('DJANGO_HOME_STATS_CACHE_TTL', default=60)

AUTH_RATE_LIMIT_ENABLED = env_bool('DJANGO_AUTH_RATE_LIMIT_ENABLED', default=True)
AUTH_RATE_LIMIT_ATTEMPTS = env_int('DJANGO_AUTH_RATE_LIMIT_ATTEMPTS', default=5)
AUTH_RATE_LIMIT_WINDOW_SECONDS = env_int('DJANGO_AUTH_RATE_LIMIT_WINDOW_SECONDS', default=300)
AUTH_RATE_LIMIT_PATHS = env_list(
    'DJANGO_AUTH_RATE_LIMIT_PATHS',
    default='/login/,/accounts/login/,/admin/login/',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': env_value('DJANGO_LOG_LEVEL', default='INFO'),
    },
}
