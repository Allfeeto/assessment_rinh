from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Ядро системы'

    def ready(self):
        from .default_lookups import register_core_lookups

        register_core_lookups()
