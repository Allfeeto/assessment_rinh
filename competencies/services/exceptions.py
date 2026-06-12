from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndicatorIssue:
    severity: str
    message: str
    table_number: int | None = None
    row_number: int | None = None
    code: str = ''

    def display(self) -> str:
        location = []
        if self.table_number is not None:
            location.append(f'таблица {self.table_number}')
        if self.row_number is not None:
            location.append(f'строка {self.row_number}')
        if self.code:
            location.append(self.code)
        prefix = f'[{", ".join(location)}] ' if location else ''
        return f'{prefix}{self.message}'


class IndicatorImportError(Exception):
    """Базовая пользовательская ошибка импорта индикаторов."""

    def __init__(self, message: str, *, issues: list[IndicatorIssue] | None = None, batch_id=None):
        super().__init__(message)
        self.issues = issues or []
        self.batch_id = batch_id


class IndicatorValidationError(IndicatorImportError):
    """Ошибка входного файла или строк индикаторов."""


class IndicatorParsingError(IndicatorImportError):
    """Ошибка чтения структуры DOCX."""


class IndicatorMappingError(IndicatorImportError):
    """Ошибка сопоставления индикаторов с компетенциями программы."""
