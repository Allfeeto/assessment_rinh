from django.apps import AppConfig


class DisciplinesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'disciplines'
    verbose_name = 'Дисциплины'

    def ready(self):
        from .lookups import register_discipline_lookups

        register_discipline_lookups()
