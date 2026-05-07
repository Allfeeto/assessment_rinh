from django.apps import AppConfig


class CompetenciesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'competencies'
    verbose_name = 'Компетенции'

    def ready(self):
        from .lookups import register_competence_lookups

        register_competence_lookups()
