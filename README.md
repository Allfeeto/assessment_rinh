# Assessment RINH

Assessment RINH - Django-приложение для ведения банка оценочных материалов в связке с образовательными программами, дисциплинами учебных планов, компетенциями, кафедрами и преподавателями.

Проект не является системой прохождения тестов студентами. В коде нет студенческих попыток, сессий тестирования, журнала оценок или публичного REST API для прохождения тестов. Основной сценарий - подготовка, хранение, проверка связей и экспорт оценочных материалов.

## Возможности

- справочники уровней образования, типов компетенций, типов заданий, ученых степеней и званий;
- кафедры, преподаватели и назначения преподавателей на дисциплины учебных планов;
- направления подготовки, профили и образовательные программы;
- импорт образовательных программ из `.plx`;
- корзина образовательных программ с восстановлением, просмотром состава и окончательным удалением;
- дисциплины учебных планов и матрица `дисциплина учебного плана -> компетенция`;
- создание и редактирование оценочных заданий с несколькими компетенциями;
- строки заданий для выбора ответа, соответствия, последовательности и открытого ответа;
- рабочее место преподавателя с session clipboard для копирования и вставки заданий;
- read-only рабочая область для заданий из корзины;
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
- `python-docx` для генерации Word-документов;
- shell-скрипты `pg_dump`/`pg_restore` для backup/restore.

В репозитории нет `pyproject.toml`, `Pipfile`, nginx-конфига, systemd unit-файлов, CI/CD-конфигурации, Celery, Redis или отдельного frontend framework.

## Структура репозитория

```text
assessment_rinh/
├─ assessment_rinh/       # настройки, ASGI/WSGI, корневые urls
├─ core/                  # справочники, home stats, lookup registry, middleware, CRUD helpers
├─ teachers/              # кафедры, преподаватели, назначения
├─ programs/              # направления, профили, программы, PLX import, корзина программ
├─ disciplines/           # дисциплины и дисциплины учебных планов
├─ competencies/          # компетенции и матрица дисциплина-компетенция
├─ assessment/            # задания, строки, clipboard, cloning, рабочие области
│  └─ services/           # item types, competence sync, clipboard, cloning, DB error formatting
├─ reports/               # отчеты
├─ export/                # Word export
├─ templates/             # HTML-шаблоны
├─ static/                # исходные CSS/JS
├─ DB_info/               # только несекретные SQL-артефакты, разрешенные к коммиту
├─ db_init/               # init-скрипты PostgreSQL для пустого Docker volume
├─ scripts/               # backup/restore scheduler scripts
├─ backups/               # runtime backups; в Git только .gitkeep
├─ tests/                 # pytest tests
├─ Dockerfile
├─ docker-compose.yml
├─ manage.py
└─ requirements.txt
```

Секреты, полные SQL-схемы, дампы, backup-файлы, `.plx` и `.env` не должны попадать в Git. `.gitignore` игнорирует `*.sql`, `*.dump`, `*.backup`, `*.bak`, `*.plx`, `.env*`; исключения сделаны только для `.env.example`, `backups/.gitkeep` и `DB_info/educational_program_trash.sql`.

## Django-приложения

| Приложение | Назначение |
| --- | --- |
| `core` | Справочники `EducationLevel`, `CompetenceType`, `AssessmentItemType`, `AcademicDegree`, `AcademicTitle`; главная страница; lookup registry; auth rate limit middleware; shared CRUD classes. |
| `teachers` | `Department`, `Teacher`, `TeacherProgramDiscipline`; dashboard кафедр и преподавателей; управление назначениями; lookup builders преподавателей и кафедр. |
| `programs` | `TrainingDirection`, `ProgramProfile`, `EducationalProgram`; dashboard программ; PLX import; корзина программ; lookup builders направлений, профилей и программ. |
| `disciplines` | `Discipline`, `ProgramDiscipline`; управление дисциплинами учебного плана; lookup builders дисциплин и дисциплин учебных планов. |
| `competencies` | `Competence`, `DisciplineCompetence`; dashboard компетенций и матрицы; deprecated compatibility endpoint для формы задания; lookup builder компетенций. |
| `assessment` | `AssessmentItem`, `AssessmentItemRow`, `AssessmentItemCompetence`; формы заданий; рабочее место; trash workspace; clipboard; cloning; sync компетенций. |
| `reports` | Фильтры и selectors для отчетов, без собственных предметных моделей. |
| `export` | Форма, selectors, preparers и renderer для `.docx`, без собственных предметных моделей. |

## Модель данных и схема БД

Предметные модели объявлены с `managed = False`. Django не создает и не изменяет предметные таблицы через migrations.

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
- `Competence` принадлежит одной образовательной программе.
- `DisciplineCompetence` задает допустимые компетенции для дисциплины учебного плана.
- `AssessmentItem` связан с `ProgramDiscipline`, типом задания и legacy-полем `competence`.
- Фактический набор компетенций задания хранится в `AssessmentItemCompetence`.
- `AssessmentItem.competence` синхронизируется с первой выбранной компетенцией для совместимости с существующей схемой.
- `AssessmentItemRow` хранит строки задания; валидные поля зависят от типа задания.

В `core/schema_contract.py` зафиксированы обязательные DB-объекты, которые должны существовать в PostgreSQL: constraints/indexes, функции и триггеры проверки связей, типа строк задания, префикса профиля и года набора.

Проверка подключенной базы:

```powershell
python manage.py check_db_schema --live
```

Проверка приватного SQL-файла без добавления его в Git:

```powershell
python manage.py check_db_schema --sql C:\secure\private_schema.sql
```

Путь также можно передать через `DB_SCHEMA_SQL_PATH`.

## Migrations

Для локальных приложений отключены migration-модули через `MIGRATION_MODULES` в `assessment_rinh/settings/base.py`:

- `core`;
- `teachers`;
- `programs`;
- `competencies`;
- `disciplines`;
- `assessment`;
- `reports`;
- `export`.

В каталогах `migrations/` оставлены только `__init__.py`.

`python manage.py migrate` не поднимет предметную схему проекта. Он может применить только стандартные Django migrations для `auth`, `admin`, `contenttypes`, `sessions` и других managed-приложений. Предметная схема должна быть восстановлена из production backup или применена из приватного SQL-артефакта развертывания.

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
| `web` | Django + gunicorn, перед запуском выполняет `collectstatic --noinput`; порт опубликован как `127.0.0.1:8000:8000`. |
| `db` | PostgreSQL 17 с volume `postgres_data` и healthcheck `pg_isready`. |
| `db-backup` | Scheduler для weekly/monthly backup через `pg_dump`; зависит от healthy `db`. |

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

Полные SQL-схемы и backup-файлы не должны коммититься. В Git отслеживается только `DB_info/educational_program_trash.sql`.

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

## Авторизация и permissions

Используются стандартные `django.contrib.auth`, `sessions`, `admin`.

Admin site дополнительно ограничен в `assessment_rinh/urls.py`: доступ к `/admin/` получает только активный superuser через `is_platform_admin`.

Ролевые helpers находятся в `core/permissions.py`:

- `is_platform_admin` - active superuser;
- `is_domain_manager` - active superuser, staff, группа `Старший преподаватель` или пользователь с набором доменных permissions;
- `can_use_teacher_workspace` - domain manager или пользователь со связанным `Teacher`;
- `can_manage_teacher_assignments` - domain manager или пользователь с permissions на `TeacherProgramDiscipline`.

Команда настройки групп:

```powershell
python manage.py setup_teacher_group
```

Она создает/обновляет:

- `Преподаватель` - ограниченный набор permissions для работы с заданиями;
- `Старший преподаватель` - permissions по доменным приложениям, кроме admin logentry.

Большинство пользовательских разделов защищены `LoginRequiredMixin` и ручным scope-фильтром по назначенным дисциплинам. CRUD-доступ для domain manager определяется через `is_domain_manager`, а не только через raw model permissions.

## Security notes

- Не коммитьте `.env`, SQL-схемы, dumps, `.backup`, `.plx` и файлы из `backups/`.
- В production используйте `DJANGO_ENV=prod`, уникальный `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, корректный `DJANGO_ALLOWED_HOSTS` и HTTPS.
- `docker-compose.yml` публикует web только на `127.0.0.1:8000`; внешний TLS/reverse proxy настраивается вне репозитория.
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

- `templates/base.html` - общая навигация, flash messages, подключение `static/js/base.js`;
- `static/js/base.js` - autocomplete, dependent selects, auto-submit GET-фильтров;
- `templates/assessment/form.html` - динамическая видимость строк задания по типу и обновление чекбоксов компетенций;
- `templates/teachers/dashboard.html` - AJAX panel/toggle назначений преподавателей;
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

- domain manager видит все активные дисциплины учебных планов;
- обычный преподаватель видит только назначенные ему `ProgramDiscipline`;
- пользователь без профиля преподавателя не получает рабочий контекст;
- clipboard хранится в session под ключом `assessment_clipboard_item_ids`;
- вставка задания копирует строки и переносит только совместимые компетенции.

`/programs/trash/`:

- удаление программы из обычного UI переводит ее в корзину через `ProgramTrashService`;
- заполняются `is_deleted`, `deleted_at`, `deleted_by`, `delete_reason`;
- связанные дисциплины, компетенции, матрица, задания, строки и назначения сохраняются;
- restore проверяет конфликт с активной программой того же профиля, кафедры и года;
- hard delete разрешен только для программы в корзине и удаляет только данные этой программы.

`/assessment/trash-workspace/`:

- используется для просмотра и копирования старых заданий из программ в корзине;
- вставка выполняется только в активный целевой контекст.

## PLX import

URL: `/programs/`.

Файлы сервиса:

- `programs/services/plx_parser.py`;
- `programs/services/plx_mapping.py`;
- `programs/services/plx_dto.py`;
- `programs/services/plx_import_service.py`;
- `programs/services/curriculum_replacement_service.py`;
- `programs/services/program_trash_service.py`;
- `programs/services/program_replace_service.py`;
- `programs/services/validators.py`;
- `programs/services/exceptions.py`.

Если активная программа с тем же профилем, кафедрой и годом набора уже существует, UI показывает конфликт и требует подтверждение замены. При подтверждении старая программа переносится в корзину, новая создается активной.

Валидация PLX включает диапазон года набора и соответствие кода профиля коду направления.

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

Обычные тесты используют `DJANGO_ENV=dev`, SQLite in-memory и не требуют PostgreSQL.

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
3. Запустить `python manage.py check_db_schema --live`.
4. Запустить `python manage.py check`.
5. Запустить `python manage.py seed_initial_data`.
6. Запустить `python manage.py setup_teacher_group`.
7. Создать superuser через `python manage.py createsuperuser`, если его нет.
8. Запустить `collectstatic`.
9. Запустить gunicorn или `docker compose up -d`.
10. Проверить backup scheduler и выполнить тестовый backup/restore на отдельной базе или стенде.

Для Docker:

```powershell
docker compose up -d
docker compose exec web python manage.py check
docker compose exec web python manage.py check_db_schema --live
```

В репозитории нет nginx/systemd-конфигурации. Если приложение публикуется наружу, TLS termination и reverse proxy настраиваются отдельно.

## Troubleshooting

### `relation does not exist`

Предметная схема не восстановлена или подключение указывает не на ту БД. Проверьте `DB_HOST`, `DB_NAME`, `DB_USER`, затем:

```powershell
python manage.py check_db_schema --live
```

### `check_db_schema` сообщает об отсутствующих trigger/function/index

Подключенная база не соответствует контракту моделей. Нужно применить актуальный приватный SQL/backup для этой среды. Не добавляйте приватный SQL в Git.

### Docker init-скрипт не запускается повторно

`db_init/` выполняется только при пустом `postgres_data`. Если volume уже создан, обычный restart не запускает bootstrap. Удаление volume удалит данные.

### `Invalid HTTP_HOST header`

Добавьте нужный host в `DJANGO_ALLOWED_HOSTS`.

### CSRF failure за HTTPS/proxy

Проверьте `DJANGO_CSRF_TRUSTED_ORIGINS` и передачу `X-Forwarded-Proto: https` reverse proxy.

### Login возвращает HTTP 429

Сработал `AuthRateLimitMiddleware`. Проверьте `DJANGO_AUTH_RATE_LIMIT_*` и cache backend.

### Статика не обновилась

Запустите:

```powershell
python manage.py collectstatic --noinput
```

В Docker перезапустите `web`, чтобы команда из `command` выполнилась снова.

### `pytest` не найден

`pytest` не является runtime-зависимостью. Установите его в dev-окружение:

```powershell
python -m pip install pytest
```

## Deprecated functionality

| Объект | Статус | Замена |
| --- | --- | --- |
| `/competencies/by-program-discipline/` | Deprecated compatibility endpoint для `templates/assessment/form.html`. | `/core/lookup/?kind=competence&program_discipline_id=<id>&linked_only=1` |

Legacy-поле `AssessmentItem.competence` остается частью модели и схемы для обратной совместимости. Основные связи задания с компетенциями ведутся через `AssessmentItemCompetence`.
