import os
from pathlib import Path


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


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / '.env')

environment = os.environ.get('DJANGO_ENV', 'dev').strip().lower()

if environment in {'prod', 'production'}:
    from .prod import *  # noqa: F401,F403
else:
    from .dev import *  # noqa: F401,F403
