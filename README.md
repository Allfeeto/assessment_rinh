# Assessment RINH

Assessment RINH - Django-приложение для ведения банка оценочных материалов в связке с образовательными программами, дисциплинами учебных планов, компетенциями, кафедрами и преподавателями.

Проект не является системой прохождения тестов студентами. В коде нет студенческих попыток, сессий тестирования, журнала оценок или публичного REST API для прохождения тестов. Основной сценарий - подготовка, хранение, проверка связей и экспорт оценочных материалов.

## Возможности

- справочники уровней образования, типов компетенций, типов заданий, ученых степеней и званий;
- кафедры, преподаватели и назначения преподавателей на дисциплины учебных планов;
- направления подготовки, профили и образовательные программы;
- импорт образовательных программ из `.plx`;
- импорт индикаторов достижения компетенций из файлов Word `.doc` и `.docx`;
- предпросмотр и безопасное обновление существующей образовательной программы из `.plx` без потери заданий и назначений;
- корзина образовательных программ с восстановлением, просмотром состава и окончательным удалением;
- дисциплины учебных планов с кодами PLX, кафедрами дисциплин и статусом присутствия в актуальном учебном плане;
- матрица `дисциплина учебного плана -> компетенция`;
- создание и редактирование оценочных заданий с несколькими компетенциями;
- строки заданий для выбора ответа, соответствия, последовательности и открытого ответа;
- рабочее место преподавателя с session clipboard для копирования и вставки заданий;
- read-only рабочая область для заданий из корзины;
- кафедральное разграничение прав для старших преподавателей;
- отчеты по покрытию компетенций и распределению заданий;
- экспорт оценочных материалов в `.docx`;
- общий autocomplete lookup для форм и фильтров;
- PostgreSQL backup/restore через Docker-сервис.

## Технологии

Источник истины по Python-зависимостям - `requirements.txt`.

Ключевые runtime-компоненты:

- Python 3.12;
- Django 5.1.4;
- PostgreSQL 17 в `docker-compose.yml`;
- `psycopg2-binary` для PostgreSQL;
- `gunicorn` для WSGI-запуска в контейнере;
- `whitenoise` для отдачи собранной статики;
- `python-docx` для чтения импортируемых `.docx` и генерации Word-документов;
- LibreOffice Writer в Docker/Linux и Microsoft Word COM при прямом запуске на Windows для временного преобразования бинарных `.doc` в `.docx`;
- HTML templates, CSS и vanilla JavaScript без отдельного frontend build step;
- shell-скрипты `pg_dump`/`pg_restore` для backup/restore.

В репозитории нет `pyproject.toml`, `Pipfile`, nginx-конфига, systemd unit-файлов, CI/CD-конфигурации, Celery, Redis или отдельного frontend framework.

## Краткая справка для ВКР

Проект реализует внутреннюю информационную систему для подготовки, хранения, контроля связей и выгрузки оценочных материалов образовательных программ. Основные пользователи: администратор платформы, старший преподаватель/ответственный по кафедре и преподаватель.

Краткая технологическая характеристика:

- язык программирования backend - Python 3.12;
- web framework - Django 5.1.4;
- СУБД - PostgreSQL 17;
- интерфейс - server-rendered Django templates, HTML, CSS, vanilla JavaScript;
- контейнеризация и запуск сервисов - Docker, Docker Compose;
- production WSGI-запуск - Gunicorn;
- работа со статикой - WhiteNoise;
- экспорт документов - `.docx` через `python-docx`;
- резервное копирование - `pg_dump`/`pg_restore` в отдельном Docker-сервисе;
- тестирование - `pytest` и Django test utilities.

С точки зрения ВКР проект можно описывать как автоматизацию учета банка оценочных материалов и связей между образовательными программами, учебными дисциплинами, компетенциями, кафедрами и преподавателями. Более подробные тезисы под структуру ВКР вынесены в `DB_info/vkr_project_notes.md`.

## Структура репозитория

```text
assessment_rinh/
├─ assessment_rinh/       # настройки, ASGI/WSGI, корневые urls
├─ core/                  # справочники, home stats, lookup registry, middleware, CRUD helpers
├─ teachers/              # кафедры, преподаватели, назначения
├─ programs/              # направления, профили, программы, PLX import/update, корзина программ
├─ disciplines/           # дисциплины, коды/кафедры PLX и дисциплины учебных планов
├─ competencies/          # компетенции, индикаторы, Word import и матрица дисциплина-компетенция
├─ assessment/            # задания, строки, clipboard, cloning, рабочие области
│  └─ services/           # item types, competence sync, clipboard, cloning, DB error formatting
├─ reports/               # отчеты
├─ export/                # Word export
├─ templates/             # HTML-шаблоны
├─ static/                # исходные CSS/JS
├─ DB_info/               # несекретные SQL-артефакты и вспомогательные заметки по БД/ВКР
├─ db_init/               # init-скрипты PostgreSQL для пустого Docker volume
├─ scripts/               # backup/restore scheduler scripts и production schema helpers
├─ backups/               # runtime backups; в Git только .gitkeep
├─ tests/                 # pytest tests
├─ Dockerfile
├─ docker-compose.yml
├─ manage.py
└─ requirements.txt
```

Секреты, полные SQL-схемы, дампы, backup-файлы, `.plx` и `.env` не должны попадать в Git. `.gitignore` игнорирует `*.sql`, `*.dump`, `*.backup`, `*.bak`, `*.plx`, `.env*`; исключения сделаны только для `.env.example`, `backups/.gitkeep` и `DB_info/educational_program_trash.sql`.

Локальные `.sql`, `.backup` и `.plx` файлы внутри `DB_info/` могут существовать на рабочей машине, но они не считаются актуальным источником схемы проекта. Перед использованием SQL-артефакта проверяйте его через `python manage.py check_db_schema --sql <path>`.

## Django-приложения

| Приложение | Назначение |
| --- | --- |
| `core` | Справочники `EducationLevel`, `CompetenceType`, `AssessmentItemType`, `AcademicDegree`, `AcademicTitle`; главная страница; lookup registry; auth rate limit middleware; shared CRUD classes. |
| `teachers` | `Department`, `Teacher`, `TeacherProgramDiscipline`; dashboard кафедр и преподавателей; управление назначениями; несколько кафедр преподавателя; lookup builders преподавателей и кафедр. |
| `programs` | `TrainingDirection`, `ProgramProfile`, `EducationalProgram`, `ProgramPlxImportDraft`; dashboard программ; PLX import/update; корзина программ; lookup builders направлений, профилей и программ. |
| `disciplines` | `Discipline`, `ProgramDiscipline`; управление дисциплинами учебного плана, кодами PLX, кафедрами дисциплин и статусом актуальности; lookup builders дисциплин и дисциплин учебных планов. |
| `competencies` | `Competence`, `CompetenceIndicator`, `CompetenceIndicatorImport`, `DisciplineCompetence`; dashboard компетенций и матрицы; импорт индикаторов из Word; lookup builder компетенций. |
| `assessment` | `AssessmentItem`, `AssessmentItemRow`, `AssessmentItemCompetence`; формы заданий; рабочее место; trash workspace; clipboard; cloning; sync компетенций. |
| `reports` | Фильтры и selectors для отчетов, без собственных предметных моделей. |
| `export` | Форма, selectors, preparers и renderer для `.docx`, без собственных предметных моделей. |

## Модель данных и схема БД

Предметные модели объявлены с `managed = False`, поэтому обычный migration flow не создает предметную схему целиком. Исключение составляют явно включаемые ручные точечные migrations, описанные ниже.

Основная цепочка:

```text
EducationLevel
  -> TrainingDirection
    -> ProgramProfile
      -> EducationalProgram
        -> ProgramDiscipline
          -> DisciplineCompetence
          -> AssessmentItem
```

Ключевые правила:

- `EducationalProgram` привязан к профилю, кафедре и году набора.
- `ProgramDiscipline` задает дисциплину в контексте конкретной образовательной программы.
- `ProgramDiscipline.discipline_code` хранит код позиции дисциплины из учебного плана PLX, например `Б1.О.07`.
- `ProgramDiscipline.department` хранит кафедру, указанную для дисциплины в PLX.
- `ProgramDiscipline.is_active_in_plan` показывает, есть ли строка в актуальной версии учебного плана; при PLX update отсутствующие строки помечаются неактивными, но не удаляются физически.
- `Competence` принадлежит одной образовательной программе.
- `CompetenceIndicator` хранит отдельный индикатор вида `ПК-1.1` и связан с программной `Competence`.
- `CompetenceIndicatorImport` хранит audit-результат загрузки Word-файла без сохранения файла или строк в session.
- Для импортируемой компетенции обязателен полный набор `КОД.1`, `КОД.2`, `КОД.3`: тексты должны начинаться с `Знает`, `Умеет`, `Владеет`. Компетенция, для которой индикаторы еще не импортировались, может иметь нулевой набор; UI и Word export показывают прочерк без ошибки.
- `DisciplineCompetence` задает допустимые компетенции для дисциплины учебного плана.
- `AssessmentItem` связан с `ProgramDiscipline`, типом задания и legacy-полем `competence`.
- Фактический набор компетенций задания хранится в `AssessmentItemCompetence`.
- `AssessmentItem.competence` синхронизируется с первой выбранной компетенцией для совместимости с существующей схемой.
- `AssessmentItemRow` хранит строки задания; валидные поля зависят от типа задания.
- `Teacher.department` остается основной кафедрой, а `Teacher.departments` хранит все кафедры преподавателя через таблицу `teacher_departments`.

В проекте важно различать две кафедры:

- `EducationalProgram.department` - кафедра, ответственная за образовательную программу;
- `ProgramDiscipline.department` - кафедра дисциплины из строки учебного плана PLX;
- право старшего преподавателя создавать и изменять компетенции проверяется по `EducationalProgram.department`;
- права старшего преподавателя на матрицу, назначения и дисциплины учебного плана проверяются по `ProgramDiscipline.department`, а фильтр "Кафедра образовательной программы" в рабочей области фильтрует именно `EducationalProgram.department`.

В `core/schema_contract.py` зафиксированы обязательные DB-объекты, которые должны существовать в PostgreSQL: таблицы связей, constraints/indexes, функции и триггеры проверки связей, типа строк задания, префикса профиля и года набора.

Проверка подключенной базы:

```powershell
python manage.py check_db_schema --live
```

Проверка приватного SQL-файла без добавления его в Git:

```powershell
python manage.py check_db_schema --sql C:\secure\private_schema.sql
```

Путь также можно передать через `DB_SCHEMA_SQL_PATH`.

## Дисциплины учебного плана

`ProgramDiscipline` - это не просто связь "программа -> дисциплина". После обновлений запись хранит контекст строки учебного плана:

- образовательную программу;
- справочную дисциплину;
- код дисциплины из PLX, например `Б1.О.07`;
- кафедру дисциплины;
- признак `is_active_in_plan`, который показывает наличие строки в последнем актуальном PLX.

Страница `/disciplines/` показывает два уровня данных: общий справочник дисциплин и дисциплины учебных планов. Для дисциплин учебного плана выводятся код, образовательная программа, кафедра дисциплины, статус актуальности PLX, количество связанных компетенций и заданий.

Обычная дисциплина может встречаться в нескольких образовательных программах, но в рамках одной образовательной программы пара `educational_program + discipline` уникальна. Если в PLX встречаются повторяющиеся строки, сервис импорта нормализует их через alias и сохраняет связи компетенций.

Старший преподаватель может добавлять или изменять дисциплину учебного плана только в пределах своих кафедр управления. Для таких пользователей кафедра дисциплины обязательна; дисциплина без кафедры не может быть назначена и изменена старшим преподавателем.

## Migrations

Предметные модели остаются `managed = False`, потому что основная production-схема управляется вне обычного Django migration flow. По умолчанию migration-модули локальных приложений отключены через `MIGRATION_MODULES` в `assessment_rinh/settings/base.py`:

- `core`;
- `teachers`;
- `programs`;
- `competencies`;
- `disciplines`;
- `assessment`;
- `reports`;
- `export`.

Исключение: для безопасных точечных DDL-изменений есть ручные migrations в приложениях `teachers`, `disciplines`, `competencies` и `programs`. Они включаются только при `DJANGO_ENABLE_LOCAL_MIGRATIONS=1`.

Сейчас такие migrations добавляют:

- таблицу `teacher_departments` для нескольких кафедр преподавателя;
- поля `ProgramDiscipline.discipline_code`, `ProgramDiscipline.department`, `ProgramDiscipline.is_active_in_plan`;
- индексы для поиска по коду дисциплины, кафедре и статусу актуальности учебного плана;
- таблицы `competence_indicator`, `competence_indicator_import` и их constraints/indexes;
- таблицу `program_plx_import_draft` для серверного хранения структурированного PLX preview.

Обычный `python manage.py migrate` без env-флага не поднимет предметную схему проекта. Он может применить только стандартные Django migrations для `auth`, `admin`, `contenttypes`, `sessions` и других managed-приложений. Предметная схема должна быть восстановлена из production backup, применена из приватного SQL-артефакта развертывания или обновлена точечными migrations через `DJANGO_ENABLE_LOCAL_MIGRATIONS=1`.

Для уже существующей production-базы не выполняйте команды, которые пересоздают volume или очищают данные. В Docker особенно важно не запускать `docker compose down -v`, если цель не состоит в полном удалении базы.

## Переменные окружения

Настройки читают `.env` из корня проекта через собственный loader в `assessment_rinh/settings/__init__.py` и `base.py`. Файл `.env` не коммитится. `.env.example` содержит только демонстрационные значения, которые нужно заменить перед реальным развертыванием.

### Основные Django-переменные

| Переменная | Назначение |
| --- | --- |
| `DJANGO_ENV` | `dev` или `prod`. По умолчанию используется `dev`. |
| `DJANGO_SECRET_KEY` | Секретный ключ Django. В `prod` обязателен. |
| `DJANGO_DEBUG` | В `dev` по умолчанию `True`, в `base` `False`; в production не включать. |
| `DJANGO_ALLOWED_HOSTS` | Список host-ов через запятую. В `prod` обязателен. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origin-ы для CSRF через запятую, если приложение работает за HTTPS-доменом/proxy. |
| `DJANGO_LOG_LEVEL` | Уровень root-логгера, по умолчанию `INFO`. |
| `DB_SCHEMA_SQL_PATH` | Локальный путь к приватному SQL-файлу для `check_db_schema --sql`. |
| `DJANGO_ENABLE_LOCAL_MIGRATIONS` | Включает ручные local migrations для `teachers`, `disciplines`, `competencies` и `programs`; по умолчанию `False`. |

### База данных

| Переменная | Назначение |
| --- | --- |
| `DB_ENGINE` | Django database backend, по умолчанию `django.db.backends.postgresql`. |
| `DB_NAME` | Имя БД приложения. |
| `DB_USER` | Пользователь БД для Django. |
| `DB_PASSWORD` | Пароль БД. Не оставлять пустым в production. |
| `DB_HOST` | Host PostgreSQL. В Docker обычно `db`. |
| `DB_PORT` | Порт PostgreSQL, обычно `5432`. |
| `POSTGRES_DB` | Имя БД для контейнера PostgreSQL и backup scripts. |
| `POSTGRES_USER` | Пользователь PostgreSQL для контейнера и backup scripts. |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL для контейнера и backup scripts. |

### Cache, sessions и rate limit

| Переменная | Назначение |
| --- | --- |
| `DJANGO_CACHE_BACKEND` | Django cache backend, по умолчанию `django.core.cache.backends.locmem.LocMemCache`. |
| `DJANGO_CACHE_LOCATION` | Cache location, по умолчанию `assessment-rinh-default`. |
| `DJANGO_HOME_STATS_CACHE_TTL` | TTL статистики главной страницы в секундах, по умолчанию `60`. |
| `DJANGO_AUTH_RATE_LIMIT_ENABLED` | Включает rate limit неудачных POST-логинов, по умолчанию `True`. |
| `DJANGO_AUTH_RATE_LIMIT_ATTEMPTS` | Количество неудачных попыток, по умолчанию `5`. |
| `DJANGO_AUTH_RATE_LIMIT_WINDOW_SECONDS` | Окно rate limit в секундах, по умолчанию `300`. |
| `DJANGO_AUTH_RATE_LIMIT_PATHS` | Пути логина через запятую, по умолчанию `/login/,/accounts/login/,/admin/login/`. |

### Production security

Эти переменные используются только в `assessment_rinh/settings/prod.py`:

| Переменная | Назначение |
| --- | --- |
| `DJANGO_SECURE_SSL_REDIRECT` | HTTPS redirect, по умолчанию `True`. |
| `DJANGO_SESSION_COOKIE_SECURE` | Secure session cookie, по умолчанию `True`. |
| `DJANGO_CSRF_COOKIE_SECURE` | Secure CSRF cookie, по умолчанию `True`. |
| `DJANGO_SECURE_HSTS_SECONDS` | HSTS max-age, по умолчанию `31536000`. |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | HSTS includeSubDomains, по умолчанию `True`. |
| `DJANGO_SECURE_HSTS_PRELOAD` | HSTS preload, по умолчанию `True`. |

`prod.py` также включает `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`, `SESSION_COOKIE_HTTPONLY = True`, `CSRF_COOKIE_HTTPONLY = True`, `X_FRAME_OPTIONS = 'DENY'`, `SECURE_CONTENT_TYPE_NOSNIFF = True` и `SECURE_REFERRER_POLICY = 'same-origin'`.

### Backup scheduler

| Переменная | Назначение |
| --- | --- |
| `BACKUP_DIR` | Корень backup-директории внутри контейнера. В compose задано `/backups`. |
| `BACKUP_DB_HOST` | Host БД для backup/restore. В compose задано `db`. |
| `BACKUP_DB_PORT` | Порт БД для backup/restore. В compose задано `5432`. |
| `BACKUP_RUN_HOUR` | Час запуска scheduler, по умолчанию `3`. |
| `BACKUP_RUN_MINUTE` | Минута запуска scheduler, по умолчанию `0`. |
| `BACKUP_WEEKLY_DAY` | День недели для weekly backup: `0` воскресенье, `1` понедельник, ..., `6` суббота. |
| `BACKUP_MONTHLY_DAY` | День месяца для monthly backup, по умолчанию `1`. |
| `TZ` | Таймзона scheduler, по умолчанию `Europe/Moscow`. |

## Локальная установка

Пример для Windows PowerShell из корня проекта:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

После копирования `.env` замените демонстрационные значения секретов и паролей.

Перед запуском приложения нужна PostgreSQL-база с предметной схемой проекта. `migrate` не создает таблицы `educational_program`, `assessment_item`, `discipline_competence` и другие предметные таблицы.

Базовая проверка Django:

```powershell
python manage.py check
```

Проверка схемы подключенной PostgreSQL-базы:

```powershell
python manage.py check_db_schema --live
```

Заполнение базовых справочников:

```powershell
python manage.py seed_initial_data
```

Создание групп преподавателей:

```powershell
python manage.py setup_teacher_group
```

Создание администратора:

```powershell
python manage.py createsuperuser
```

Запуск dev-сервера:

```powershell
python manage.py runserver
```

## Запуск через Docker Compose

`docker-compose.yml` содержит три сервиса:

| Сервис | Назначение |
| --- | --- |
| `web` | Django + gunicorn, перед запуском выполняет `collectstatic --noinput`; порт опубликован как `8000:8000`; `restart: unless-stopped`. |
| `db` | PostgreSQL 17 с volume `postgres_data`, healthcheck `pg_isready` и `restart: unless-stopped`. |
| `db-backup` | Scheduler для weekly/monthly backup через `pg_dump`; зависит от healthy `db`; `restart: unless-stopped`. |

Persistent volumes:

- `postgres_data` - данные PostgreSQL;
- `media_volume` - `/app/media`;
- `static_volume` - `/app/staticfiles`;
- `./backups` - backup-файлы на host filesystem.

Первичный запуск:

```powershell
Copy-Item .env.example .env
docker compose up -d db
docker compose run --rm web python manage.py check_db_schema --live
docker compose run --rm web python manage.py seed_initial_data
docker compose run --rm web python manage.py setup_teacher_group
docker compose up -d web db-backup
```

Если база восстановлена из полного backup и уже содержит нужные данные, команды `seed_initial_data` и `setup_teacher_group` можно запускать повторно: они используют idempotent-логику создания/обновления.

Обычный перезапуск контейнеров не обнуляет базу:

```powershell
docker compose restart web
docker compose restart db-backup
```

Не удаляйте `postgres_data`, если нужно сохранить данные.

## PostgreSQL bootstrap

`db_init/01_restore.sh` выполняется официальным entrypoint PostgreSQL только при первом создании пустого `postgres_data`.

Поведение:

- если в `db_init/` лежит один из поддерживаемых `.backup` файлов, скрипт восстановит его через `pg_restore`;
- если backup не найден, скрипт завершится успешно и выведет сообщение, что для SQL bootstrap нужно положить приватный `*.sql` в `db_init/`;
- приватные `.sql` файлы выполняются официальным entrypoint PostgreSQL как часть стандартной обработки `/docker-entrypoint-initdb.d`;
- при `docker compose restart` init-скрипты не запускаются повторно.

Поддерживаемые backup-имена в `01_restore.sh`:

- `assessment_DB_docker2.backup`;
- `asssessment_DB_docker2.backup`;
- `assessment_DB_docker1.backup`.

Полные SQL-схемы и backup-файлы не должны коммититься. Из SQL-артефактов в Git отслеживается только `DB_info/educational_program_trash.sql`.

## Static и media

Настройки:

- `STATIC_URL = '/static/'`;
- `STATIC_ROOT = BASE_DIR / 'staticfiles'`;
- `STATICFILES_DIRS = [BASE_DIR / 'static']`;
- `MEDIA_URL = '/media/'`;
- `MEDIA_ROOT = BASE_DIR / 'media'`;
- staticfiles storage - `whitenoise.storage.CompressedStaticFilesStorage`.

Сборка статики вручную:

```powershell
python manage.py collectstatic --noinput
```

В Docker `web` выполняет `collectstatic --noinput` перед запуском gunicorn.

## Backup system

Backup реализован Docker-сервисом `db-backup`. Host cron и systemd в репозитории не используются.

Скрипты:

- `scripts/db-backup.sh` - ручной weekly/monthly backup;
- `scripts/db-backup-scheduler.sh` - бесконечный scheduler с daily polling по времени;
- `scripts/db-restore.sh` - restore из `.dump`.

Формат backup - custom dump PostgreSQL (`pg_dump --format=custom`). Файлы:

```text
backups/
  weekly/
    weekly.dump
  monthly/
    monthly.dump
```

Retention фиксированный: один weekly и один monthly файл. Новый успешный backup атомарно заменяет файл того же типа.

Запуск всего стека вместе с scheduler:

```powershell
docker compose up -d
```

Проверка scheduler:

```powershell
docker compose ps db-backup
docker compose logs --tail=100 db-backup
```

Ручной weekly backup:

```powershell
docker compose run --rm db-backup sh /usr/local/bin/db-backup.sh weekly
```

Ручной monthly backup:

```powershell
docker compose run --rm db-backup sh /usr/local/bin/db-backup.sh monthly
```

Проверка файла:

```powershell
docker compose run --rm db-backup sh -c "ls -l /backups/weekly/weekly.dump && test -s /backups/weekly/weekly.dump"
```

Проверка читаемости backup:

```powershell
docker compose run --rm db-backup pg_restore --list /backups/weekly/weekly.dump
```

## Restore backup

Restore перезаписывает объекты в целевой базе через `pg_restore --clean --if-exists --no-owner --no-privileges`.

Перед restore остановите web, чтобы приложение не писало в БД:

```powershell
docker compose stop web
docker compose run --rm db-backup sh /usr/local/bin/db-restore.sh /backups/weekly/weekly.dump
docker compose start web
```

Для monthly backup:

```powershell
docker compose stop web
docker compose run --rm db-backup sh /usr/local/bin/db-restore.sh /backups/monthly/monthly.dump
docker compose start web
```

После restore:

```powershell
docker compose exec web python manage.py check
docker compose exec web python manage.py check_db_schema --live
```

## Production schema update helpers

`scripts/prod_apply_plx_department_changes.sh` предназначен для аккуратного применения точечных изменений схемы, связанных с кафедрами дисциплин PLX и несколькими кафедрами преподавателя.

Скрипт:

- работает из корня проекта;
- выбирает Docker Compose или direct host mode через `APPLY_MODE=auto|docker|direct`;
- перед миграциями создает PostgreSQL custom backup в `backups/pre_migration` или в `BACKUP_DIR_HOST`;
- запускает `DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py migrate`;
- выполняет `python manage.py check`, `check_db_schema --live` и дополнительную проверку таблицы `teacher_departments`;
- проверяет, что основная кафедра преподавателя не потерялась при переносе в M2M.

Пример запуска на сервере:

```bash
sh scripts/prod_apply_plx_department_changes.sh
```

Дополнительные точечные helpers:

- `scripts/prod_apply_competence_indicator_changes.sh` проверяет наличие конвертера `.doc`, создает backup, применяет migration `competencies` для таблиц индикаторов и проверяет итоговую схему;
- `scripts/prod_apply_programs_ux_changes.sh` создает backup, применяет migration `programs.0002_plx_import_draft` и проверяет таблицу серверных PLX-черновиков.

## Авторизация и permissions

Используются стандартные `django.contrib.auth`, `sessions`, `admin`.

Admin site дополнительно ограничен в `assessment_rinh/urls.py`: доступ к `/admin/` получает только активный superuser через `is_platform_admin`.

Ролевые helpers находятся в `core/permissions.py`:

- `is_platform_admin` - active superuser;
- `is_superuser_or_platform_admin` - active superuser, staff или пользователь с набором platform permissions без группы `Старший преподаватель`;
- `is_domain_manager` - platform admin или участник группы `Старший преподаватель`;
- `is_senior_teacher` - active пользователь из группы `Старший преподаватель`;
- `get_user_departments` - кафедры, которыми пользователь может управлять;
- `can_use_teacher_workspace` - domain manager или пользователь со связанным `Teacher`;
- `can_manage_teacher_assignments` - platform admin, старший преподаватель с кафедрами управления или пользователь с permissions на `TeacherProgramDiscipline`;
- `can_manage_competence` - проверка права на компетенцию по кафедре ее образовательной программы;
- `can_manage_program_discipline` - проверка права на дисциплину учебного плана и матрицу по кафедре конкретной дисциплины;
- `can_assign_teacher_to_program_discipline` - проверка, что преподаватель и дисциплина относятся к допустимой кафедре.

Команда настройки групп:

```powershell
python manage.py setup_teacher_group
```

Она создает/обновляет:

- `Преподаватель` - ограниченный набор permissions для работы с заданиями;
- `Старший преподаватель` - permissions по доменным приложениям, кроме admin logentry.

Большинство пользовательских разделов защищены `LoginRequiredMixin` и ручным scope-фильтром. Superuser/staff видит все данные, старший преподаватель управляет только своими кафедрами, обычный преподаватель видит назначенные ему дисциплины учебных планов.

Правила для старшего преподавателя:

- группа `Старший преподаватель` дает вход в доменные разделы, но не делает пользователя platform admin;
- пользователь управляет кафедрами, привязанными к его карточке `Teacher`: основная кафедра `Teacher.department` плюс M2M `Teacher.departments`;
- справочник кафедр изменяет только superuser/staff, старший преподаватель видит свои кафедры;
- старший преподаватель может создавать и редактировать преподавателей только в своих кафедрах, при редактировании чужие кафедральные связи преподавателя сохраняются;
- удаление преподавателей доступно только superuser/staff;
- назначение преподавателя на дисциплину разрешено только если кафедра дисциплины входит в кафедры управления пользователя и преподаватель относится к этой кафедре;
- компетенции можно создавать и изменять только для образовательных программ своих кафедр; чужие компетенции не показываются в управляемом списке и недоступны по прямой ссылке;
- связи матрицы можно создавать и изменять только для дисциплин учебного плана своих кафедр;
- дисциплина без указанной кафедры не может быть назначена старшим преподавателем;
- в панели назначений уже назначенные или чужие дисциплины могут оставаться видимыми, но checkbox отключается с причиной запрета.

## Назначения преподавателей

Назначения хранятся в `TeacherProgramDiscipline`: преподаватель привязывается не к общей дисциплине, а к конкретной дисциплине учебного плана (`ProgramDiscipline`). Поэтому одно и то же название дисциплины в разных программах, с разными PLX-кодами или кафедрами, является разным контекстом назначения.

Основной интерфейс находится на `/teachers/`:

- таблица кафедр показывает только доступные пользователю кафедры;
- таблица преподавателей для старшего преподавателя ограничена его кафедрами управления;
- таблица существующих назначений показывает связи преподавателей с дисциплинами учебных планов;
- AJAX-панель `/teachers/assignments/panel/` строит строки дисциплин выбранной программы;
- JSON endpoint `/teachers/assignments/toggle/` включает или снимает назначение и повторно проверяет права на сервере.

Панель назначений показывает код дисциплины PLX, название, кафедру дисциплины, статус актуальности учебного плана и других назначенных преподавателей. Строки сортируются так, чтобы уже назначенные дисциплины были сверху, затем шли доступные для назначения, затем недоступные. Поиск работает по названию дисциплины и `discipline_code`.

Для старшего преподавателя checkbox включен только если выполнены оба условия:

- кафедра дисциплины входит в его кафедры управления;
- назначаемый преподаватель связан с этой же кафедрой через основную кафедру или `Teacher.departments`.

Если условие не выполнено, строка может оставаться видимой для контроля, но действие блокируется с текстовой причиной. Та же проверка используется в формах и во view, поэтому ограничение не зависит только от интерфейса.

## Security notes

- Не коммитьте `.env`, SQL-схемы, dumps, `.backup`, `.plx` и файлы из `backups/`.
- В production используйте `DJANGO_ENV=prod`, уникальный `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, корректный `DJANGO_ALLOWED_HOSTS` и HTTPS.
- `docker-compose.yml` публикует web как `8000:8000`. Если сервер доступен извне, ограничьте bind address или настройте внешний TLS/reverse proxy вне репозитория.
- `prod.py` включает HTTPS redirect, secure cookies, HSTS и базовые security headers.
- Если приложение стоит за reverse proxy, proxy должен передавать `X-Forwarded-Proto: https`, иначе возможны HTTPS redirect loop или неверная оценка secure request.
- `CSRF_TRUSTED_ORIGINS` должен содержать реальные HTTPS origin-ы, если домен отличается от host/port запроса.
- Backup-директория содержит чувствительные данные. Храните ее на persistent storage с ограниченными правами доступа.
- Не запускайте `docker compose down -v` на сервере с нужными данными.

## Lookup/autocomplete architecture

Публичный endpoint:

```text
/core/lookup/
```

Формат ответа:

```json
{"results": [{"id": 1, "label": "..." }]}
```

Основные query-параметры:

- `kind` - тип lookup;
- `q` - строка поиска;
- `limit` - лимит, нормализуется в диапазон `1..50`;
- `selected_id` - вернуть текущий выбранный объект;
- `deleted_only` / `include_deleted` - режим поиска по активным программам или корзине;
- `purpose` - контекст прав, например `assignment`, `teacher_management`, `program_discipline_management`;
- дополнительные параметры фильтрации зависят от `kind`.

Registry находится в `core/lookups.py`. `core.views.lookup_options` не знает о доменных моделях и получает builder через registry.

Регистрация builders выполняется в `AppConfig.ready()` со стороны приложений:

- `core/default_lookups.py` - `auth_user`, `assessment_item_type`;
- `teachers/lookups.py` - `department`, `teacher`;
- `programs/lookups.py` - `training_direction`, `program_profile`, `educational_program`;
- `disciplines/lookups.py` - `discipline`, `program_discipline`;
- `competencies/lookups.py` - `competence`.

Поддерживаемые `kind`:

- `assessment_item_type`;
- `auth_user`;
- `competence`;
- `department`;
- `discipline`;
- `educational_program`;
- `program_discipline`;
- `program_profile`;
- `teacher`;
- `training_direction`.

Frontend-обвязка находится в `static/js/base.js`. Поля получают атрибуты через `core.forms.apply_autocomplete_attrs` или напрямую в шаблонах: `data-autocomplete-kind`, `data-autocomplete-url`, `data-autocomplete-parent`, `data-autocomplete-dynamic-params`, `data-autocomplete-extra`.

Lookup-логика учитывает права пользователя:

- обычный преподаватель получает только назначенные ему дисциплины учебных планов;
- старший преподаватель получает данные в пределах кафедр управления;
- superuser/staff получает полный активный scope;
- для корзины используются `deleted_only=1` или `mode=trash`;
- `program_discipline` ищется по названию дисциплины, коду `discipline_code`, кафедре дисциплины, программе, году набора и кафедре образовательной программы.

Deprecated compatibility endpoint:

```text
/competencies/by-program-discipline/
```

Он оставлен для `templates/assessment/form.html` и делегирует в generic competence lookup. Замена:

```text
/core/lookup/?kind=competence&program_discipline_id=<id>&linked_only=1
```

## Frontend integration

Frontend построен на Django templates, CSS и vanilla JavaScript:

- `templates/base.html` - общая навигация, flash messages, адаптивное верхнее меню и подключение общих JS-модулей;
- `static/js/base.js` - autocomplete, dependent selects, auto-submit GET-фильтров;
- `static/js/compact_blocks.js` - раскрытие, сворачивание и пагинация независимых dashboard-блоков без полной перезагрузки страницы;
- `static/js/async_blocks.js` - поиск, сортировка и пагинация обычных списков с заменой только соответствующего блока;
- `templates/assessment/form.html` - динамическая видимость строк задания по типу и обновление чекбоксов компетенций;
- `templates/teachers/dashboard.html` - AJAX panel/toggle назначений преподавателей;
- `templates/programs/includes/plx_preview_group.html` - группы предпросмотра изменений при безопасном PLX update;
- `static/css/base.css` - общий стиль.

Отдельного build step, npm, webpack/vite или frontend package manager в репозитории нет.

## Основные URL

| URL | Назначение |
| --- | --- |
| `/` | Главная страница. |
| `/login/`, `/accounts/login/` | Вход. |
| `/logout/`, `/accounts/logout/` | Выход. |
| `/admin/` | Django admin, только superuser. |
| `/core/lookup/` | Generic JSON lookup/autocomplete. |
| `/core/education-levels/` | Справочник уровней образования. |
| `/core/competence-types/` | Справочник типов компетенций. |
| `/core/assessment-item-types/` | Справочник типов заданий. |
| `/core/academic-degrees/` | Справочник ученых степеней. |
| `/core/academic-titles/` | Справочник ученых званий. |
| `/teachers/` | Dashboard кафедр, преподавателей и назначений. |
| `/teachers/assignments/panel/` | AJAX panel назначений преподавателей. |
| `/teachers/assignments/toggle/` | JSON toggle назначения преподавателя. |
| `/programs/` | Dashboard программ и PLX import. |
| `/competencies/indicators/import/` | POST endpoint импорта индикаторов выбранной образовательной программы из `.doc`/`.docx`. |
| `/programs/trash/` | Корзина образовательных программ. |
| `/disciplines/` | Управление дисциплинами выбранной программы. |
| `/disciplines/overview/` | Обзор дисциплин и дисциплин учебных планов. |
| `/competencies/` | Dashboard компетенций и матрицы. |
| `/competencies/by-program-discipline/` | Deprecated JSON endpoint для формы задания. |
| `/assessment/` | Список оценочных заданий. |
| `/assessment/workspace/` | Рабочее место преподавателя. |
| `/assessment/trash-workspace/` | Просмотр и копирование заданий из корзины. |
| `/reports/` | Отчеты. |
| `/export/` | Redirect на `/export/word/`. |
| `/export/word/` | Экспорт Word. |

CRUD-маршруты сущностей находятся в соответствующих `urls.py`.

## Оценочные задания

Форма задания:

- `AssessmentItemForm`;
- `AssessmentItemRowCreateFormSet`;
- `AssessmentItemRowUpdateFormSet`;
- `BaseAssessmentItemRowFormSet`.

Сервисная логика разделена в `assessment/services/`:

- `item_types.py` - коды типов, UI labels, разбор строк для detail/export;
- `competence_sync.py` - получение и синхронизация компетенций задания;
- `clipboard.py` - session clipboard;
- `cloning.py` - перенос задания в другую дисциплину учебного плана;
- `db_errors.py` - преобразование DB errors в пользовательские сообщения;
- `__init__.py` - compatibility exports для старых импортов `assessment.services`.

Поддерживаемые типы:

- `single` - выбор одного ответа;
- `multiple` - выбор нескольких ответов;
- `matching` - установление соответствия;
- `sequence` - установление последовательности;
- `open` - открытый ответ.

Серверная валидация строк:

- выбор одного ответа: минимум два варианта и ровно один верный;
- выбор нескольких ответов: минимум два варианта и минимум один верный;
- соответствие: минимум одна пара, правые дистракторы допустимы;
- последовательность: минимум два шага, порядок назначается формой;
- открытый ответ: минимум один допустимый ответ.

## Рабочее место и корзина

`/assessment/workspace/`:

- superuser/staff видит все дисциплины учебных планов из неудаленных образовательных программ;
- старший преподаватель видит дисциплины учебных планов, кафедра дисциплины которых входит в его кафедры управления;
- обычный преподаватель видит только назначенные ему `ProgramDiscipline` из неудаленных программ;
- пользователь без профиля преподавателя не получает рабочий контекст;
- фильтры включают год набора, кафедру образовательной программы, образовательную программу, дисциплину учебного плана, компетенцию, тип задания и размер страницы;
- если выбранная программа или дисциплина больше не попадает в доступный scope, view сбрасывает невалидное значение и выбирает первый доступный вариант;
- дисциплины в выпадающем списке сортируются по `discipline_code`, затем по названию;
- в контексте выбранной дисциплины показывается кафедра дисциплины и пометка, если строка отсутствует в последнем PLX;
- задания группируются по типу задания, внутри группы новые записи идут выше старых;
- clipboard хранится в session под ключом `assessment_clipboard_item_ids`;
- копирование кладет в clipboard только доступные пользователю задания;
- вставка задания копирует строки и переносит только совместимые компетенции целевой дисциплины учебного плана.

`/programs/trash/`:

- удаление программы из обычного UI переводит ее в корзину через `ProgramTrashService`;
- заполняются `is_deleted`, `deleted_at`, `deleted_by`, `delete_reason`;
- связанные дисциплины, компетенции, матрица, задания, строки и назначения сохраняются;
- restore проверяет конфликт с активной программой того же профиля, кафедры и года;
- hard delete разрешен только для программы в корзине и удаляет только данные этой программы.

`/assessment/trash-workspace/`:

- используется для просмотра и копирования старых заданий из программ в корзине;
- работает с теми же фильтрами, но ищет только по удаленным образовательным программам;
- дополнительно поддерживает поиск по части текста задания через `q`;
- открытие задания выполняется в read-only режиме;
- копирование из корзины кладет старые задания в тот же session clipboard;
- вставка выполняется только в активный целевой контекст обычной рабочей области.

## PLX import

URL: `/programs/`.

Файлы сервиса:

- `programs/services/validators.py` - проверка расширения `.plx`, пустого файла и лимита размера `8 MB`;
- `programs/services/plx_parser.py`;
- `programs/services/plx_mapping.py`;
- `programs/services/plx_dto.py`;
- `programs/services/plx_import_service.py`;
- `programs/services/plx_update_service.py`;
- `programs/services/curriculum_replacement_service.py`;
- `programs/services/program_trash_service.py`;
- `programs/services/program_replace_service.py`;
- `programs/services/exceptions.py`.

Pipeline обработки:

1. `PlxParser` читает XML/PLX: корневой узел `Документ`, блок `diffgram`, dataset `dsMMISDB`, таблицы `Планы`, `ООП`, вложенные `ООП`, `Кафедры`, `ПланыСтроки`, `ПланыКомпетенции`, `ПланыКомпетенцииДисциплины`.
2. `PlxMapper` нормализует данные в `PlxProgramImportDTO`: уровень образования, направление, профиль, кафедру программы, дисциплины, компетенции и связи дисциплина-компетенция.
3. `PlxImportService` создает новую программу или выполняет полную замену через корзину.
4. `PlxProgramUpdateService` строит dry-run preview и применяет безопасное обновление существующей программы в транзакции.

Важные правила mapping:

- активный профиль выбирается по `КодАктивногоООП`, единственному `Используется=true` или единственной вложенной `ООП`;
- кафедра программы берется из `Планы.КодПрофКафедры`, а если его нет - из единственного `ПланыПрофили.КодПодразделения`;
- дисциплины берутся из `ПланыСтроки` только для текущего плана, с `СчитатьВПлане=true`, без строк `ТипОбъекта=5` и без строк, начинающихся с `элективные дисциплины`;
- для дисциплины сохраняются название, внешний id строки, `ДисциплинаКод` и кафедра из `КодКафедры`;
- одинаковые строки дисциплин с тем же названием и кодом схлопываются через alias, а разные коды одного названия сохраняют связи компетенций;
- компетенции берутся только для базового или активного ООП, удаленные строки пропускаются;
- дубли компетенций с одинаковым кодом допускаются только при совпадающих названии и типе, связи перенаправляются через alias;
- тип компетенции определяется по префиксу `УК`, `ОПК`, `ПК` или числовому типу PLX.

Если активная программа с тем же профилем, кафедрой и годом набора уже существует, UI показывает конфликт и предлагает:

- отменить импорт;
- выполнить полную замену: старая программа переносится в корзину, новая создается активной;
- выполнить безопасное обновление существующей программы с предварительным просмотром изменений.

Безопасное PLX update сохраняет `ProgramDiscipline` primary keys, поэтому существующие оценочные задания и назначения преподавателей остаются привязанными к тем же строкам учебного плана, если строку можно сопоставить по `discipline_code` или уникальному названию. Дисциплины, отсутствующие в новом PLX, помечаются `is_active_in_plan=False`, но не удаляются автоматически.

Preview PLX update группирует изменения:

- новые дисциплины, компетенции, связи и кафедры;
- изменения метаданных программы, дисциплин и компетенций;
- дисциплины, компетенции и связи, которых больше нет в новом PLX;
- предупреждения и блокирующие конфликты.

Блокирующие конфликты запрещают применение. Предупреждения показываются пользователю, но не всегда блокируют update: например, дисциплина отсутствует в новом PLX, но имеет задания или назначения, поэтому она сохраняется и помечается как неактуальная.

## Импорт индикаторов компетенций

Отдельный блок импорта находится на `/programs/` и не связан с PLX pipeline.

- пользователь явно выбирает активную образовательную программу;
- platform admin может выбрать любую активную программу, старший преподаватель - только программу своей кафедры;
- принимаются бинарные Word-файлы `.doc` из фактического источника и `.docx`;
- максимальный размер загружаемого файла - 10 МБ;
- `.doc` временно преобразуется в `.docx` через LibreOffice в Docker/Linux; при прямом запуске на Windows используется Microsoft Word COM, причем исходный `.doc` открывается read-only; затем общий parser читает полученный `.docx`;
- временные файлы конвертации удаляются после обработки;
- таблицы находятся по смысловому заголовку `Индикаторы достижения компетенции`;
- ячейка с несколькими кодами (`ПК-1.1`, `ПК-1.2`, `ПК-1.3`) разбивается на отдельные записи;
- для каждой представленной в файле компетенции требуется ровно три индикатора: `.1` - `Знает`, `.2` - `Умеет`, `.3` - `Владеет`; неполный набор, лишний код или неверная роль блокируют импорт;
- компетенции сопоставляются по нормализованному коду только внутри выбранной программы и автоматически не создаются;
- неизвестная или неоднозначная компетенция блокирует импорт индикаторов;
- повторный импорт пропускает точные дубли и обновляет текст существующего `(competence, code)`;
- импорт выполняется транзакционно, исходный файл и строки не сохраняются в session;
- `CompetenceIndicatorImport` сохраняет имя и SHA-256 файла, пользователя, программу, статус, счетчики и отчет об ошибках; `CompetenceIndicator` хранит код, текст, файл-источник и номера таблицы/строки;
- platform admin и старший преподаватель в пределах кафедры программы могут вручную редактировать полный набор индикаторов в форме компетенции; коды `.1`, `.2`, `.3` формируются автоматически, а частичный набор не сохраняется;
- страница `/competencies/` показывает для каждой компетенции позиции `Знать`, `Уметь`, `Владеть`; отсутствующие индикаторы отображаются прочерками.

Сервисы находятся в `competencies/services/indicator_*`. Пакеты импорта и индикаторы доступны в Django admin.

## UX и загрузка больших списков

Dashboard-страницы и большие списки используют компактные серверные preview-блоки, серверную пагинацию и частичное обновление HTML-фрагментов. Кнопки раскрытия/сворачивания, переходы между страницами, поиск и сортировка заменяют только нужный блок, поэтому страница не прыгает в начало и не загружает все строки из БД.

Страница `/programs/` использует независимые query-параметры:

- `directions_expanded`, `directions_page`;
- `profiles_expanded`, `profiles_page`;
- `programs_expanded`, `programs_page`, `programs_per_page`;
- `indicator_imports_expanded`, `indicator_imports_page`.

В свернутом состоянии загружаются только первые 8 строк справочных блоков и 3 последних импорта индикаторов. В раскрытом состоянии используется серверная пагинация. Выбор программы для импорта индикаторов работает через generic autocomplete `/core/lookup/`.

Во время PLX preview/confirm страница переходит в явный `plx_import_active`-режим. Структурированный PLX DTO хранится в таблице `program_plx_import_draft`, а в session находится только ID черновика. Черновики действуют 24 часа и удаляются при отмене или успешном применении.

Валидация PLX включает диапазон года набора, соответствие кода профиля коду направления, уникальность кодов дисциплин учебного плана и корректность кафедр дисциплин.

## Reports и Word export

`/reports/` строит таблицы по фильтрам:

- образовательная программа;
- дисциплина;
- компетенция;
- тип задания;
- размер страницы.

Selectors учитывают как legacy `AssessmentItem.competence`, так и `AssessmentItemCompetence`.

`/export/word/` генерирует `.docx` через `export/services.py` и `export/docx_renderer.py`.

Ограничения export:

- обязательны образовательная программа и дисциплина;
- связка программы и дисциплины должна быть активной;
- максимум `1000` заданий за один экспорт;
- шаблон документа - `templates/export/maket.docx`;
- первая таблица группирует задания по компетенциям и выводит соответствующие индикаторы; если индикаторы не заполнены, используется прочерк;
- при отсутствии заданий или превышении лимита view возвращает форму с ошибкой.

## Management commands

| Команда | Назначение |
| --- | --- |
| `python manage.py check_db_schema --live` | Проверяет подключенную БД на соответствие unmanaged-моделям и обязательным DB objects. |
| `python manage.py check_db_schema --sql <path>` | Проверяет приватный SQL-файл схемы без подключения к БД. |
| `python manage.py seed_initial_data` | Создает/обновляет базовые уровни образования, типы компетенций, типы заданий, ученые степени и звания. |
| `python manage.py setup_teacher_group` | Создает/обновляет группы `Преподаватель` и `Старший преподаватель` с permissions. |
| `python manage.py createsuperuser` | Стандартная команда Django для superuser. |
| `python manage.py collectstatic --noinput` | Сбор static в `staticfiles`. |
| `DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py migrate` | Применяет ручные local migrations для `teachers`, `disciplines`, `competencies` и `programs`; использовать только после backup. |
| `python manage.py check` | Django system checks. |

## Logging, sessions и cache

Logging:

- настроен root logger с console handler;
- уровень задается через `DJANGO_LOG_LEVEL`;
- логи пишут `assessment.views`, `export.*`, `programs.services.*` и другие модули.

Sessions:

- стандартный Django session middleware;
- clipboard заданий хранится в session;
- в production cookies защищаются настройками из `prod.py`.

Cache:

- по умолчанию `LocMemCache`;
- используется для home stats и auth rate limit;
- home stats cache key: `core:home_stats`;
- при переносе/восстановлении/окончательном удалении программы cache статистики очищается.

## Tests

В репозитории есть `pytest.ini`, `conftest.py` и тесты в `tests/`.

`pytest` не входит в `requirements.txt`, поэтому для локального запуска тестов его нужно установить в dev-окружение отдельно:

```powershell
python -m pip install pytest
pytest -q
```

Обычные тесты используют `DJANGO_ENV=dev`, SQLite in-memory и не требуют PostgreSQL. Покрыты selectors, schema contract, PLX mapping/import/update, импорт `.doc`/`.docx` индикаторов, кафедральные permissions, фильтры рабочих областей и dashboard smoke checks.

PostgreSQL invariant tests помечены `postgres_integration` и запускаются только при:

```powershell
$env:RUN_POSTGRES_INTEGRATION_TESTS='1'
pytest -q -m postgres_integration
```

Для них нужна реальная PostgreSQL-база, совместимая со схемой проекта.

## Production deployment notes

Минимальный production flow:

1. Подготовить `.env` с `DJANGO_ENV=prod`, секретами, host-ами, DB credentials и HTTPS/CSRF настройками.
2. Подготовить PostgreSQL: восстановить production backup или применить приватный SQL bootstrap вне Git.
3. Если среда еще не содержит точечных DDL-изменений PLX/кафедр, выполнить `scripts/prod_apply_plx_department_changes.sh` или вручную применить migrations с `DJANGO_ENABLE_LOCAL_MIGRATIONS=1` после backup.
4. Для добавления импорта индикаторов сначала пересобрать и перезапустить web-образ с LibreOffice (`docker compose build web && docker compose up -d web`), затем отдельно выполнить `sh scripts/prod_apply_competence_indicator_changes.sh`; скрипт создаёт backup и применяет только migration `competencies`.
5. Для UX-доработки страницы программ и серверных PLX-черновиков выполнить `sh scripts/prod_apply_programs_ux_changes.sh`; скрипт создаёт backup и применяет только migration `programs.0002_plx_import_draft`.
6. Запустить `python manage.py check_db_schema --live`.
7. Запустить `python manage.py check`.
8. Запустить `python manage.py seed_initial_data`.
9. Запустить `python manage.py setup_teacher_group`.
10. Создать superuser через `python manage.py createsuperuser`, если его нет.
11. Запустить `collectstatic`.
12. Запустить gunicorn или `docker compose up -d`.
13. Проверить backup scheduler и выполнить тестовый backup/restore на отдельной базе или стенде.

Для Docker:

```powershell
docker compose up -d
docker compose exec web python manage.py check
docker compose exec web python manage.py check_db_schema --live
```

В репозитории нет nginx/systemd-конфигурации. Если приложение публикуется наружу, TLS termination и reverse proxy настраиваются отдельно.


