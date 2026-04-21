class PlxImportError(Exception):
    """Базовая ошибка импорта PLX."""


class PlxValidationError(PlxImportError):
    """Ошибка валидации входного файла/данных."""


class PlxParsingError(PlxImportError):
    """Ошибка парсинга XML/PLX."""


class PlxMappingError(PlxImportError):
    """Ошибка сопоставления данных PLX с бизнес-моделью."""


class PlxConflictError(PlxImportError):
    """Конфликт: программа с теми же признаками уже существует."""

    def __init__(self, message: str, *, existing_program_id: int | None = None):
        super().__init__(message)
        self.existing_program_id = existing_program_id

