from django.apps import AppConfig


class ProgramsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'programs'
    verbose_name = 'Направления и программы'

    def ready(self):
        from .lookups import register_program_lookups

        register_program_lookups()
