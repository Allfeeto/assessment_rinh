from __future__ import annotations

from .exceptions import PlxValidationError


MAX_PLX_UPLOAD_SIZE = 8 * 1024 * 1024


def validate_uploaded_plx_file(uploaded_file) -> None:
    """Базовая валидация загружаемого файла PLX."""
    if uploaded_file is None:
        raise PlxValidationError('Файл не выбран.')

    filename = (getattr(uploaded_file, 'name', '') or '').strip()
    if not filename:
        raise PlxValidationError('Не удалось определить имя загруженного файла.')

    if not filename.lower().endswith('.plx'):
        raise PlxValidationError('Разрешена загрузка только файлов с расширением .plx.')

    if hasattr(uploaded_file, 'size'):
        if uploaded_file.size == 0:
            raise PlxValidationError('Загружен пустой файл.')
        if uploaded_file.size > MAX_PLX_UPLOAD_SIZE:
            raise PlxValidationError('Размер файла .plx не должен превышать 8 МБ.')


def ensure_required(value: str | None, field_name: str) -> str:
    if value is None:
        raise PlxValidationError(f'Не найдено обязательное значение: {field_name}.')
    stripped = value.strip()
    if not stripped:
        raise PlxValidationError(f'Пустое обязательное значение: {field_name}.')
    return stripped
