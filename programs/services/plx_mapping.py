from __future__ import annotations

import re

from .exceptions import PlxMappingError, PlxValidationError
from .plx_dto import (
    CompetenceDTO,
    DepartmentInfoDTO,
    DisciplineCompetenceLinkDTO,
    DisciplineDTO,
    PlxProgramImportDTO,
    ProgramInfoDTO,
)
from .plx_parser import ParsedPlxDocument
from .validators import ensure_required

PROFILE_CODE_RE = re.compile(r'^\s*(\d+(?:\.\d+)+)\s+(.+?)\s*$')
COMPETENCE_TYPE_BY_NUMERIC = {
    '2': 'УК',
    '3': 'ОПК',
    '4': 'ПК',
}


def normalize_text(value: str | None) -> str:
    if value is None:
        return ''
    return ' '.join(str(value).replace('\u00a0', ' ').strip().split())


def normalize_key(value: str | None) -> str:
    return normalize_text(value).casefold()


def _to_bool(value: str | None) -> bool:
    return normalize_key(value) in {'true', '1', 'да'}


def _map_education_level_name(raw_name: str) -> str:
    value = normalize_key(raw_name)
    if 'бакалавр' in value:
        return 'бакалавриат'
    if 'магистр' in value:
        return 'магистратура'
    if 'специал' in value:
        return 'специалитет'
    return normalize_text(raw_name)


def _split_profile_name(raw_name: str, fallback_code: str) -> tuple[str, str]:
    text = normalize_text(raw_name)
    match = PROFILE_CODE_RE.match(text)
    if match:
        return match.group(1), normalize_text(match.group(2))
    if fallback_code:
        return fallback_code, text
    raise PlxMappingError('Не удалось определить код профиля из данных PLX.')


def _resolve_competence_type_name(row: dict[str, str]) -> str:
    code = normalize_text(row.get('ШифрКомпетенции'))
    prefix = code.split('-', 1)[0].upper()
    if prefix in {'УК', 'ОПК', 'ПК'}:
        return prefix
    numeric = normalize_text(row.get('Тип'))
    return COMPETENCE_TYPE_BY_NUMERIC.get(numeric, 'ПК')


class PlxMapper:
    """Слой сопоставления ParsedPlxDocument в нормализованный DTO."""

    def map_to_dto(self, parsed: ParsedPlxDocument) -> PlxProgramImportDTO:
        plan = self._get_single(parsed, 'Планы')
        plan_code = ensure_required(plan.get('Код'), 'Планы.Код')
        main_oop_code = ensure_required(plan.get('КодООП'), 'Планы.КодООП')
        active_oop_code = normalize_text(plan.get('КодАктивногоООП')) or None

        year_raw = ensure_required(plan.get('ГодНачалаПодготовки'), 'Планы.ГодНачалаПодготовки')
        try:
            admission_year = int(year_raw)
        except ValueError as exc:
            raise PlxMappingError('Некорректный год набора в файле PLX.') from exc

        main_oop = self._find_row(parsed.table('ООП'), 'Код', main_oop_code)
        if not main_oop:
            raise PlxMappingError('Не найдено базовое ООП для импортируемого плана.')

        nested_oop = [
            row
            for row in parsed.table('ООП_вложенные')
            if normalize_text(row.get('КодРодительскогоООП')) == main_oop_code
        ]
        if not nested_oop:
            raise PlxMappingError('Не найдены профили (вложенные ООП) в файле PLX.')

        active_oop = None
        if active_oop_code:
            active_oop = self._find_row(nested_oop, 'Код', active_oop_code)
        if active_oop is None:
            active_oop = self._find_first_true(nested_oop, 'Используется')
        if active_oop is None:
            active_oop = nested_oop[0]

        training_direction_code = ensure_required(main_oop.get('Шифр'), 'ООП.Шифр')
        training_direction_name = ensure_required(main_oop.get('Название'), 'ООП.Название')

        profile_fallback_code = self._fallback_profile_code(parsed.source_filename)
        profile_code, profile_name = _split_profile_name(
            raw_name=ensure_required(active_oop.get('Название'), 'Активное ООП.Название'),
            fallback_code=profile_fallback_code,
        )

        education_level_name = self._resolve_education_level_name(parsed)

        department = self._resolve_department(parsed, plan)

        disciplines = self._extract_disciplines(parsed, plan_code)
        competences = self._extract_competences(parsed, plan_code, main_oop_code, active_oop.get('Код'))
        links = self._extract_links(parsed, disciplines=disciplines, competences=competences)

        return PlxProgramImportDTO(
            source_filename=parsed.source_filename,
            program=ProgramInfoDTO(
                education_level_name=education_level_name,
                training_direction_code=training_direction_code,
                training_direction_name=training_direction_name,
                profile_code=profile_code,
                profile_name=profile_name,
                admission_year=admission_year,
            ),
            department=department,
            disciplines=disciplines,
            competences=competences,
            discipline_competence_links=links,
        )

    @staticmethod
    def _get_single(parsed: ParsedPlxDocument, table_name: str) -> dict[str, str]:
        rows = parsed.table(table_name)
        if not rows:
            raise PlxMappingError(f'Не найдена таблица "{table_name}" в PLX.')
        return rows[0]

    @staticmethod
    def _find_row(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str] | None:
        target = normalize_text(value)
        for row in rows:
            if normalize_text(row.get(key)) == target:
                return row
        return None

    @staticmethod
    def _find_first_true(rows: list[dict[str, str]], key: str) -> dict[str, str] | None:
        for row in rows:
            if _to_bool(row.get(key)):
                return row
        return None

    @staticmethod
    def _fallback_profile_code(filename: str) -> str:
        base = filename.rsplit('.', 1)[0]
        return normalize_text(base.split('_', 1)[0])

    def _resolve_education_level_name(self, parsed: ParsedPlxDocument) -> str:
        level_code = normalize_text(parsed.document_attrs.get('КодУровняОбразования'))
        if level_code:
            for row in parsed.table('Уровень_образования'):
                if normalize_text(row.get('Код_записи')) == level_code:
                    return _map_education_level_name(row.get('Уровень', ''))

        level_name = normalize_text(parsed.document_attrs.get('УровеньОбразования'))
        if level_name:
            return _map_education_level_name(level_name)
        raise PlxValidationError('Не удалось определить уровень образования из файла PLX.')

    def _resolve_department(self, parsed: ParsedPlxDocument, plan: dict[str, str]) -> DepartmentInfoDTO:
        department_code = normalize_text(plan.get('КодПрофКафедры'))
        if not department_code:
            profile_rows = parsed.table('ПланыПрофили')
            if profile_rows:
                department_code = normalize_text(profile_rows[0].get('КодПодразделения'))

        if not department_code:
            raise PlxMappingError('Не найден код кафедры в файле PLX.')

        department_row = None
        for row in parsed.table('Кафедры'):
            if normalize_text(row.get('Код')) == department_code:
                department_row = row
                break
            if normalize_text(row.get('Номер')) == department_code:
                department_row = row
                break

        if department_row is None:
            raise PlxMappingError(
                f'Не найдена кафедра с кодом/номером "{department_code}" в таблице "Кафедры".'
            )

        number = normalize_text(department_row.get('Номер')) or normalize_text(department_row.get('Код'))
        short_name = normalize_text(department_row.get('Сокращение'))
        full_name = normalize_text(department_row.get('Название'))

        if not number or not short_name or not full_name:
            raise PlxMappingError('Недостаточно данных по кафедре в файле PLX.')

        return DepartmentInfoDTO(number=number, short_name=short_name, full_name=full_name)

    def _extract_disciplines(self, parsed: ParsedPlxDocument, plan_code: str) -> list[DisciplineDTO]:
        result: list[DisciplineDTO] = []
        seen_names: set[str] = set()

        for row in parsed.table('ПланыСтроки'):
            if normalize_text(row.get('КодПлана')) != plan_code:
                continue
            if not _to_bool(row.get('СчитатьВПлане')):
                continue
            if normalize_text(row.get('ТипОбъекта')) == '5':
                continue

            name = normalize_text(row.get('Дисциплина'))
            if not name:
                continue
            if normalize_key(name).startswith('элективные дисциплины'):
                continue

            key = normalize_key(name)
            if key in seen_names:
                continue
            seen_names.add(key)

            external_id = ensure_required(row.get('Код'), 'ПланыСтроки.Код')
            result.append(
                DisciplineDTO(
                    external_id=external_id,
                    code=normalize_text(row.get('ДисциплинаКод')),
                    name=name,
                )
            )

        if not result:
            raise PlxMappingError('Не удалось извлечь дисциплины из PLX.')
        return result

    def _extract_competences(
        self,
        parsed: ParsedPlxDocument,
        plan_code: str,
        main_oop_code: str,
        active_oop_code: str | None,
    ) -> list[CompetenceDTO]:
        valid_oop_codes = {normalize_text(main_oop_code)}
        if active_oop_code:
            valid_oop_codes.add(normalize_text(active_oop_code))

        result: list[CompetenceDTO] = []
        seen_codes: set[str] = set()

        for row in parsed.table('ПланыКомпетенции'):
            if normalize_text(row.get('КодПлана')) != plan_code:
                continue
            if _to_bool(row.get('Удалена')):
                continue
            if normalize_text(row.get('КодООП')) not in valid_oop_codes:
                continue

            competence_code = normalize_text(row.get('ШифрКомпетенции'))
            if not competence_code:
                continue
            code_key = normalize_key(competence_code)
            if code_key in seen_codes:
                continue
            seen_codes.add(code_key)

            result.append(
                CompetenceDTO(
                    external_id=ensure_required(row.get('Код'), 'ПланыКомпетенции.Код'),
                    code=competence_code,
                    name=ensure_required(row.get('Наименование'), 'ПланыКомпетенции.Наименование'),
                    competence_type_name=_resolve_competence_type_name(row),
                )
            )

        if not result:
            raise PlxMappingError('Не удалось извлечь компетенции из PLX.')
        return result

    def _extract_links(
        self,
        parsed: ParsedPlxDocument,
        *,
        disciplines: list[DisciplineDTO],
        competences: list[CompetenceDTO],
    ) -> list[DisciplineCompetenceLinkDTO]:
        discipline_ids = {item.external_id for item in disciplines}
        competence_ids = {item.external_id for item in competences}

        links: list[DisciplineCompetenceLinkDTO] = []
        seen: set[tuple[str, str]] = set()
        for row in parsed.table('ПланыКомпетенцииДисциплины'):
            discipline_external_id = normalize_text(row.get('КодСтроки'))
            competence_external_id = normalize_text(row.get('КодКомпетенции'))
            if discipline_external_id not in discipline_ids:
                continue
            if competence_external_id not in competence_ids:
                continue
            pair = (discipline_external_id, competence_external_id)
            if pair in seen:
                continue
            seen.add(pair)
            links.append(
                DisciplineCompetenceLinkDTO(
                    discipline_external_id=discipline_external_id,
                    competence_external_id=competence_external_id,
                )
            )
        return links

