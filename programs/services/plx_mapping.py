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

        active_oop = self._resolve_active_oop(nested_oop, active_oop_code)

        training_direction_code = ensure_required(main_oop.get('Шифр'), 'ООП.Шифр')
        training_direction_name = ensure_required(main_oop.get('Название'), 'ООП.Название')

        profile_fallback_code = self._fallback_profile_code(parsed.source_filename)
        profile_code, profile_name = _split_profile_name(
            raw_name=ensure_required(active_oop.get('Название'), 'Активное ООП.Название'),
            fallback_code=profile_fallback_code,
        )

        education_level_name = self._resolve_education_level_name(parsed)

        department = self._resolve_department(parsed, plan)

        disciplines, discipline_aliases = self._extract_disciplines(parsed, plan_code)
        competences, competence_aliases = self._extract_competences(
            parsed,
            plan_code,
            main_oop_code,
            active_oop.get('Код'),
        )
        links = self._extract_links(
            parsed,
            disciplines=disciplines,
            competences=competences,
            discipline_aliases=discipline_aliases,
            competence_aliases=competence_aliases,
        )

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

    def _resolve_active_oop(
        self,
        nested_oop: list[dict[str, str]],
        active_oop_code: str | None,
    ) -> dict[str, str]:
        if active_oop_code:
            active_oop = self._find_row(nested_oop, 'Код', active_oop_code)
            if active_oop is None:
                raise PlxMappingError(
                    'КодАктивногоООП указан, но соответствующий профиль не найден в файле PLX.'
                )
            return active_oop

        flagged = [row for row in nested_oop if _to_bool(row.get('Используется'))]
        if len(flagged) == 1:
            return flagged[0]
        if len(flagged) > 1:
            raise PlxMappingError(
                'В файле PLX отмечено несколько активных профилей (Используется=true).'
            )

        if len(nested_oop) == 1:
            return nested_oop[0]

        raise PlxMappingError(
            'Не удалось однозначно определить активный профиль: укажите КодАктивногоООП в PLX.'
        )

    @staticmethod
    def _fallback_profile_code(filename: str) -> str:
        base = filename.rsplit('.', 1)[0]
        return normalize_text(base.split('_', 1)[0])

    def _resolve_education_level_name(self, parsed: ParsedPlxDocument) -> str:
        level_code = normalize_text(parsed.document_attrs.get('КодУровняОбразования'))
        if level_code:
            for row in parsed.table('Уровень_образования'):
                if normalize_text(row.get('Код_записи')) == level_code:
                    mapped = _map_education_level_name(row.get('Уровень', ''))
                    if not mapped:
                        raise PlxValidationError(
                            'Найден уровень образования по коду, но его наименование пустое.'
                        )
                    return mapped

        level_name = normalize_text(parsed.document_attrs.get('УровеньОбразования'))
        if level_name:
            return _map_education_level_name(level_name)
        raise PlxValidationError('Не удалось определить уровень образования из файла PLX.')

    def _resolve_department(self, parsed: ParsedPlxDocument, plan: dict[str, str]) -> DepartmentInfoDTO:
        department_code = normalize_text(plan.get('КодПрофКафедры'))
        if not department_code:
            profile_rows = parsed.table('ПланыПрофили')
            candidate_codes = {
                normalize_text(row.get('КодПодразделения'))
                for row in profile_rows
                if normalize_text(row.get('КодПодразделения'))
            }
            if len(candidate_codes) == 1:
                department_code = next(iter(candidate_codes))
            elif len(candidate_codes) > 1:
                raise PlxMappingError(
                    'В ПланыПрофили указано несколько разных кодов подразделений; '
                    'невозможно однозначно определить кафедру.'
                )

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

    def _extract_disciplines(
        self,
        parsed: ParsedPlxDocument,
        plan_code: str,
    ) -> tuple[list[DisciplineDTO], dict[str, str]]:
        result: list[DisciplineDTO] = []
        seen_by_name: dict[str, list[DisciplineDTO]] = {}
        aliases: dict[str, str] = {}
        seen_external_ids: set[str] = set()

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

            external_id = ensure_required(row.get('Код'), 'ПланыСтроки.Код')
            if external_id in seen_external_ids:
                continue
            seen_external_ids.add(external_id)

            key = normalize_key(name)
            duplicates = seen_by_name.get(key, [])
            if duplicates:
                kept = duplicates[0]
                kept_code = normalize_text(kept.code)
                new_code = normalize_text(row.get('ДисциплинаКод'))
                # Полный дубль строки (по имени+коду) схлопываем через alias.
                if kept_code == new_code:
                    aliases[external_id] = kept.external_id
                    continue

            item = DisciplineDTO(
                external_id=external_id,
                code=normalize_text(row.get('ДисциплинаКод')),
                name=name,
            )
            seen_by_name.setdefault(key, []).append(item)
            result.append(item)

        if not result:
            raise PlxMappingError('Не удалось извлечь дисциплины из PLX.')
        return result, aliases

    def _extract_competences(
        self,
        parsed: ParsedPlxDocument,
        plan_code: str,
        main_oop_code: str,
        active_oop_code: str | None,
    ) -> tuple[list[CompetenceDTO], dict[str, str]]:
        valid_oop_codes = {normalize_text(main_oop_code)}
        if active_oop_code:
            valid_oop_codes.add(normalize_text(active_oop_code))

        result: list[CompetenceDTO] = []
        seen_by_code: dict[str, CompetenceDTO] = {}
        aliases: dict[str, str] = {}

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
            external_id = ensure_required(row.get('Код'), 'ПланыКомпетенции.Код')
            code_key = normalize_key(competence_code)
            kept = seen_by_code.get(code_key)
            if kept:
                new_name = ensure_required(row.get('Наименование'), 'ПланыКомпетенции.Наименование')
                new_type = _resolve_competence_type_name(row)
                if normalize_key(kept.name) != normalize_key(new_name):
                    raise PlxMappingError(
                        'Обнаружены компетенции с одинаковым кодом, но разными наименованиями: '
                        f'"{kept.code}".'
                    )
                if normalize_key(kept.competence_type_name) != normalize_key(new_type):
                    raise PlxMappingError(
                        'Обнаружены компетенции с одинаковым кодом, но разными типами: '
                        f'"{kept.code}".'
                    )
                aliases[external_id] = kept.external_id
                continue
            item = CompetenceDTO(
                external_id=external_id,
                code=competence_code,
                name=ensure_required(row.get('Наименование'), 'ПланыКомпетенции.Наименование'),
                competence_type_name=_resolve_competence_type_name(row),
            )
            seen_by_code[code_key] = item
            result.append(item)

        if not result:
            raise PlxMappingError('Не удалось извлечь компетенции из PLX.')
        return result, aliases

    def _extract_links(
        self,
        parsed: ParsedPlxDocument,
        *,
        disciplines: list[DisciplineDTO],
        competences: list[CompetenceDTO],
        discipline_aliases: dict[str, str] | None = None,
        competence_aliases: dict[str, str] | None = None,
    ) -> list[DisciplineCompetenceLinkDTO]:
        discipline_ids = {item.external_id for item in disciplines}
        competence_ids = {item.external_id for item in competences}
        discipline_aliases = discipline_aliases or {}
        competence_aliases = competence_aliases or {}

        links: list[DisciplineCompetenceLinkDTO] = []
        seen: set[tuple[str, str]] = set()
        for row in parsed.table('ПланыКомпетенцииДисциплины'):
            raw_discipline_external_id = normalize_text(row.get('КодСтроки'))
            discipline_external_id = discipline_aliases.get(
                raw_discipline_external_id,
                raw_discipline_external_id,
            )
            raw_competence_external_id = normalize_text(row.get('КодКомпетенции'))
            competence_external_id = competence_aliases.get(
                raw_competence_external_id,
                raw_competence_external_id,
            )
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
