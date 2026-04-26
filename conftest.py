import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assessment_rinh.settings')
os.environ.setdefault('DJANGO_ENV', 'dev')
os.environ.setdefault('DB_ENGINE', 'django.db.backends.sqlite3')
os.environ.setdefault('DB_NAME', ':memory:')

import django
from django.apps import apps

if not apps.ready:
    django.setup()
