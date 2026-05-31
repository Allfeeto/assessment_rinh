from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Count

from assessment.models import AssessmentItem, AssessmentItemCompetence
from competencies.models import Competence, DisciplineCompetence
from core.models import CompetenceType
from disciplines.models import ProgramDiscipline
from programs.models import EducationalProgram
from teachers.models import Department

from .exceptions import PlxImportError
from .plx_dto import CompetenceDTO, DisciplineDTO, PlxProgramImportDTO
from .plx_import_service import PlxImportService
from .plx_mapping import normalize_key, normalize_text

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PreviewEntry:
    label: str
    details: tuple[str, ...] = ()


@dataclass(slots=True)
class ImportConflict:
    label: str
    message: str
    severity: str = 'warning'


@dataclass(slots=True)
class PlxImportPreview:
    existing_program_id: int
    summary: dict
    additions: dict[str, list[PreviewEntry]] = field(default_factory=dict)
    changes: dict[str, list[PreviewEntry]] = field(default_factory=dict)
    missing: dict[str, list[PreviewEntry]] = field(default_factory=dict)
    conflicts: list[ImportConflict] = field(default_factory=list)

    @property
    def has_blocking_conflicts(self) -> bool:
        return any(conflict.severity == 'blocking' for conflict in self.conflicts)

    @property
    def can_apply(self) -> bool:
        return not self.has_blocking_conflicts


@dataclass(slots=True)
class PlxUpdateResult:
    program_id: int
    created_disciplines: int = 0
    updated_disciplines: int = 0
    marked_inactive_disciplines: int = 0
    created_competences: int = 0
    updated_competences: int = 0
    created_links: int = 0


@dataclass(slots=True)
class _DisciplineMatch:
    incoming: DisciplineDTO
    existing: ProgramDiscipline | None
    matched_by: str


def _entry(label: str, *details: str) -> PreviewEntry:
    return PreviewEntry(label=label, details=tuple(detail for detail in details if detail))


def _dict_of_lists(*keys: str) -> dict[str, list[PreviewEntry]]:
    return {key: [] for key in keys}


def _discipline_label_from_parts(code: str | None, name: str) -> str:
    code = normalize_text(code)
    name = normalize_text(name)
    if code:
        return f'{code} — {name}'
    return name


def _discipline_label_from_dto(item: DisciplineDTO) -> str:
    return _discipline_label_from_parts(item.code, item.name)


def _discipline_label_from_model(item: ProgramDiscipline) -> str:
    return item.discipline_display_name


def _department_label(department: Department | None) -> str:
    if department is None:
        return 'не указана'
    return f'{department.number} — {department.short_name}'


def _department_label_from_dto(item: DisciplineDTO) -> str:
    if item.department is None:
        return 'не найдена'
    return f'{item.department.number} — {item.department.short_name}'


def _competence_label(item: Competence | CompetenceDTO) -> str:
    return f'{item.code} — {item.name}'


class PlxProgramUpdateService:
    """
    Builds a dry-run diff and applies safe in-place PLX updates.

    The update path intentionally preserves ProgramDiscipline primary keys, so
    assessment items and teacher assignments stay attached to the same curriculum
    row whenever the row can be matched by discipline_code or a unique legacy name.
    """

    def __init__(self, *, import_service: PlxImportService | None = None):
        self.import_service = import_service or PlxImportService()

    def build_preview(self, dto: PlxProgramImportDTO, program: EducationalProgram) -> PlxImportPreview:
        program = (
            EducationalProgram.objects.select_related(
                'program_profile__training_direction__education_level',
                'department',
            )
            .get(pk=program.pk)
        )
        additions = _dict_of_lists('disciplines', 'competences', 'links', 'departments')
        changes = _dict_of_lists('program', 'disciplines', 'competences', 'links')
        missing = _dict_of_lists('disciplines', 'competences', 'links')
        conflicts: list[ImportConflict] = []

        current_disciplines = self._program_disciplines(program)
        matches = self._match_disciplines(dto, current_disciplines, conflicts)
        matched_existing_ids = {
            match.existing.id
            for match in matches.values()
            if match.existing is not None
        }

        self._preview_program_changes(dto, program, changes)
        self._preview_departments(dto, additions, conflicts)
        self._preview_discipline_changes(
            matches,
            current_disciplines,
            matched_existing_ids,
            additions,
            changes,
            missing,
            conflicts,
        )
        self._preview_competence_changes(dto, program, additions, changes, missing)
        self._preview_link_changes(
            dto,
            program,
            matches,
            additions,
            missing,
            conflicts,
        )

        return PlxImportPreview(
            existing_program_id=program.id,
            summary=dto.summary(),
            additions=additions,
            changes=changes,
            missing=missing,
            conflicts=conflicts,
        )

    def apply_update(self, dto: PlxProgramImportDTO, program: EducationalProgram, *, user=None) -> PlxUpdateResult:
        with transaction.atomic():
            locked_program = (
                EducationalProgram.objects.select_for_update()
                .select_related('program_profile__training_direction__education_level', 'department')
                .get(pk=program.pk)
            )
            preview = self.build_preview(dto, locked_program)
            if preview.has_blocking_conflicts:
                raise PlxImportError('В PLX есть блокирующие конфликты. Сначала исправьте файл или отмените импорт.')

            education_level = self.import_service._resolve_education_level(dto.program.education_level_name)
            direction = self.import_service._resolve_training_direction(
                code=dto.program.training_direction_code,
                name=dto.program.training_direction_name,
                education_level=education_level,
            )
            profile = self.import_service._resolve_program_profile(
                code=dto.program.profile_code,
                name=dto.program.profile_name,
                training_direction=direction,
            )
            department = self.import_service._resolve_department(
                dto.department.number,
                dto.department.short_name,
                dto.department.full_name,
            )

            program_fields: list[str] = []
            if locked_program.program_profile_id != profile.id:
                locked_program.program_profile = profile
                program_fields.append('program_profile')
            if locked_program.department_id != department.id:
                locked_program.department = department
                program_fields.append('department')
            if locked_program.admission_year != dto.program.admission_year:
                locked_program.admission_year = dto.program.admission_year
                program_fields.append('admission_year')
            if program_fields:
                locked_program.save(update_fields=program_fields)

            current_disciplines = self._program_disciplines(locked_program)
            conflicts: list[ImportConflict] = []
            matches = self._match_disciplines(dto, current_disciplines, conflicts)
            if any(conflict.severity == 'blocking' for conflict in conflicts):
                raise PlxImportError('В PLX есть блокирующие конфликты по дисциплинам.')

            result = PlxUpdateResult(program_id=locked_program.id)
            discipline_map: dict[str, ProgramDiscipline] = {}
            touched_program_discipline_ids: set[int] = set()
            processed_program_discipline_ids: set[int] = set()

            for item in dto.disciplines:
                match = matches[item.external_id]
                program_discipline = match.existing
                discipline = self.import_service._resolve_discipline(item.name)
                discipline_department = self.import_service._resolve_optional_department(item.department)
                clean_code = normalize_text(item.code) or None

                if program_discipline is None:
                    program_discipline, created = ProgramDiscipline.objects.get_or_create(
                        educational_program=locked_program,
                        discipline=discipline,
                        defaults={
                            'discipline_code': clean_code,
                            'department': discipline_department,
                            'is_active_in_plan': True,
                        },
                    )
                    if created:
                        result.created_disciplines += 1
                    touched_program_discipline_ids.add(program_discipline.id)
                    discipline_map[item.external_id] = program_discipline
                    continue

                touched_program_discipline_ids.add(program_discipline.id)
                discipline_map[item.external_id] = program_discipline
                if program_discipline.id in processed_program_discipline_ids:
                    continue
                processed_program_discipline_ids.add(program_discipline.id)

                fields_to_update: list[str] = []
                if program_discipline.discipline_id != discipline.id:
                    if ProgramDiscipline.objects.filter(
                        educational_program=locked_program,
                        discipline=discipline,
                    ).exclude(pk=program_discipline.pk).exists():
                        raise PlxImportError(
                            f'Нельзя переименовать дисциплину "{program_discipline.discipline.name}" '
                            f'в "{discipline.name}": такая связь уже есть в программе.'
                        )
                    program_discipline.discipline = discipline
                    fields_to_update.append('discipline')
                if clean_code != (program_discipline.discipline_code or None):
                    program_discipline.discipline_code = clean_code
                    fields_to_update.append('discipline_code')
                if discipline_department and program_discipline.department_id != discipline_department.id:
                    program_discipline.department = discipline_department
                    fields_to_update.append('department')
                if not program_discipline.is_active_in_plan:
                    program_discipline.is_active_in_plan = True
                    fields_to_update.append('is_active_in_plan')
                if fields_to_update:
                    program_discipline.save(update_fields=fields_to_update)
                    result.updated_disciplines += 1

            inactive_qs = ProgramDiscipline.objects.filter(
                educational_program=locked_program,
                is_active_in_plan=True,
            )
            if touched_program_discipline_ids:
                inactive_qs = inactive_qs.exclude(pk__in=touched_program_discipline_ids)
            result.marked_inactive_disciplines = inactive_qs.update(is_active_in_plan=False)

            competence_map = self._apply_competences(dto, locked_program, result)
            result.created_links = self._apply_links(dto, discipline_map, competence_map)

            logger.info(
                'PLX in-place update completed: program_id=%s user_id=%s created_disciplines=%s '
                'updated_disciplines=%s marked_inactive=%s created_competences=%s '
                'updated_competences=%s created_links=%s',
                locked_program.id,
                getattr(user, 'id', None),
                result.created_disciplines,
                result.updated_disciplines,
                result.marked_inactive_disciplines,
                result.created_competences,
                result.updated_competences,
                result.created_links,
            )
            return result

    @staticmethod
    def _program_disciplines(program: EducationalProgram) -> list[ProgramDiscipline]:
        return list(
            ProgramDiscipline.objects.filter(educational_program=program)
            .select_related('discipline', 'department')
            .annotate(
                assessment_items_total=Count('assessment_items', distinct=True),
                teacher_assignments_total=Count('teacher_program_disciplines', distinct=True),
            )
            .order_by('discipline_code', 'discipline__name', 'id')
        )

    def _match_disciplines(
        self,
        dto: PlxProgramImportDTO,
        current_disciplines: list[ProgramDiscipline],
        conflicts: list[ImportConflict],
    ) -> dict[str, _DisciplineMatch]:
        current_by_code: dict[str, list[ProgramDiscipline]] = defaultdict(list)
        current_by_name: dict[str, list[ProgramDiscipline]] = defaultdict(list)
        incoming_by_code: dict[str, list[DisciplineDTO]] = defaultdict(list)

        for item in current_disciplines:
            code = normalize_text(item.discipline_code)
            if code:
                current_by_code[code].append(item)
            current_by_name[normalize_key(item.discipline.name)].append(item)

        for item in dto.disciplines:
            code = normalize_text(item.code)
            if code:
                incoming_by_code[code].append(item)

        for code, items in incoming_by_code.items():
            if len(items) > 1:
                conflicts.append(ImportConflict(
                    label=code,
                    message='Одинаковый код дисциплины встречается в PLX несколько раз.',
                    severity='blocking',
                ))

        for code, items in current_by_code.items():
            if len(items) > 1:
                conflicts.append(ImportConflict(
                    label=code,
                    message='В текущей программе уже есть несколько дисциплин с одинаковым кодом.',
                    severity='blocking',
                ))

        matches: dict[str, _DisciplineMatch] = {}
        for item in dto.disciplines:
            code = normalize_text(item.code)
            name_key = normalize_key(item.name)
            existing: ProgramDiscipline | None = None
            matched_by = 'new'

            if code and len(current_by_code.get(code, [])) == 1:
                existing = current_by_code[code][0]
                matched_by = 'discipline_code'
            elif len(current_by_name.get(name_key, [])) == 1:
                existing = current_by_name[name_key][0]
                matched_by = 'name'
                if code and normalize_text(existing.discipline_code) != code:
                    conflicts.append(ImportConflict(
                        label=_discipline_label_from_dto(item),
                        message='Название совпало, но код дисциплины отличается. Будет обновлен код существующей строки.',
                        severity='warning',
                    ))
            elif code and not current_by_code.get(code) and len(current_by_name.get(name_key, [])) > 1:
                conflicts.append(ImportConflict(
                    label=_discipline_label_from_dto(item),
                    message='Название совпадает с несколькими текущими строками. Автоматическое сопоставление опасно.',
                    severity='blocking',
                ))

            matches[item.external_id] = _DisciplineMatch(
                incoming=item,
                existing=existing,
                matched_by=matched_by,
            )
        return matches

    @staticmethod
    def _preview_program_changes(
        dto: PlxProgramImportDTO,
        program: EducationalProgram,
        changes: dict[str, list[PreviewEntry]],
    ) -> None:
        direction = program.program_profile.training_direction
        if direction.name != normalize_text(dto.program.training_direction_name):
            changes['program'].append(_entry(
                'Направление подготовки',
                f'Название: "{direction.name}" -> "{normalize_text(dto.program.training_direction_name)}"',
            ))
        if program.program_profile.name != normalize_text(dto.program.profile_name):
            changes['program'].append(_entry(
                'Профиль программы',
                f'Название: "{program.program_profile.name}" -> "{normalize_text(dto.program.profile_name)}"',
            ))
        if program.department.short_name != normalize_text(dto.department.short_name):
            changes['program'].append(_entry(
                'Кафедра программы',
                f'Краткое название: "{program.department.short_name}" -> "{normalize_text(dto.department.short_name)}"',
            ))

    @staticmethod
    def _preview_departments(
        dto: PlxProgramImportDTO,
        additions: dict[str, list[PreviewEntry]],
        conflicts: list[ImportConflict],
    ) -> None:
        seen_numbers = set()
        for item in dto.disciplines:
            if item.department_code and item.department is None:
                conflicts.append(ImportConflict(
                    label=_discipline_label_from_dto(item),
                    message=f'Код кафедры "{item.department_code}" указан в PLX, но не найден в таблице кафедр PLX.',
                    severity='warning',
                ))
                continue
            if item.department is None:
                continue
            if item.department.number in seen_numbers:
                continue
            seen_numbers.add(item.department.number)
            if not Department.objects.filter(number=item.department.number).exists():
                additions['departments'].append(_entry(
                    f'{item.department.number} — {item.department.short_name}',
                    item.department.full_name,
                ))

    @staticmethod
    def _preview_discipline_changes(
        matches: dict[str, _DisciplineMatch],
        current_disciplines: list[ProgramDiscipline],
        matched_existing_ids: set[int],
        additions: dict[str, list[PreviewEntry]],
        changes: dict[str, list[PreviewEntry]],
        missing: dict[str, list[PreviewEntry]],
        conflicts: list[ImportConflict],
    ) -> None:
        seen_unmatched_names: set[str] = set()
        seen_existing_ids: set[int] = set()

        for match in matches.values():
            incoming = match.incoming
            existing = match.existing
            if existing is None:
                name_key = normalize_key(incoming.name)
                if name_key in seen_unmatched_names:
                    continue
                seen_unmatched_names.add(name_key)
                additions['disciplines'].append(_entry(
                    _discipline_label_from_dto(incoming),
                    f'Кафедра дисциплины: {_department_label_from_dto(incoming)}',
                ))
                continue

            if existing.id in seen_existing_ids:
                continue
            seen_existing_ids.add(existing.id)
            details = []
            if normalize_text(existing.discipline.name) != normalize_text(incoming.name):
                details.append(f'Название: "{existing.discipline.name}" -> "{normalize_text(incoming.name)}"')
                if ProgramDiscipline.objects.filter(
                    educational_program_id=existing.educational_program_id,
                    discipline__name__iexact=normalize_text(incoming.name),
                ).exclude(pk=existing.pk).exists():
                    conflicts.append(ImportConflict(
                        label=_discipline_label_from_dto(incoming),
                        message='В программе уже есть дисциплина с новым названием. Автоматическое переименование заблокировано.',
                        severity='blocking',
                    ))
            if (existing.discipline_code or '') != normalize_text(incoming.code):
                details.append(
                    f'Код: "{existing.discipline_code or "не указан"}" -> "{normalize_text(incoming.code) or "не указан"}"'
                )
            incoming_department_number = incoming.department.number if incoming.department else None
            existing_department_number = existing.department.number if existing.department else None
            if incoming_department_number and existing_department_number != incoming_department_number:
                details.append(
                    f'Кафедра: "{_department_label(existing.department)}" -> "{_department_label_from_dto(incoming)}"'
                )
            if not existing.is_active_in_plan:
                details.append('Статус: строка снова будет отмечена как присутствующая в актуальном PLX')
            if details:
                changes['disciplines'].append(_entry(_discipline_label_from_model(existing), *details))

        for item in current_disciplines:
            if item.id in matched_existing_ids:
                continue
            details = [
                'Будет помечена как отсутствующая в актуальном PLX, без физического удаления.',
                f'Заданий: {getattr(item, "assessment_items_total", 0)}',
                f'Назначений преподавателей: {getattr(item, "teacher_assignments_total", 0)}',
            ]
            missing['disciplines'].append(_entry(_discipline_label_from_model(item), *details))
            if getattr(item, 'assessment_items_total', 0) or getattr(item, 'teacher_assignments_total', 0):
                conflicts.append(ImportConflict(
                    label=_discipline_label_from_model(item),
                    message='Дисциплина отсутствует в новом PLX, но имеет задания или назначения. Она не будет удалена.',
                    severity='warning',
                ))

    @staticmethod
    def _preview_competence_changes(
        dto: PlxProgramImportDTO,
        program: EducationalProgram,
        additions: dict[str, list[PreviewEntry]],
        changes: dict[str, list[PreviewEntry]],
        missing: dict[str, list[PreviewEntry]],
    ) -> dict[str, Competence | None]:
        current_by_code = {
            normalize_text(item.code): item
            for item in Competence.objects.select_related('competence_type').filter(educational_program=program)
        }
        incoming_by_code: dict[str, CompetenceDTO] = {}
        matches: dict[str, Competence | None] = {}

        for item in dto.competences:
            code = normalize_text(item.code)
            if not code or code in incoming_by_code:
                continue
            incoming_by_code[code] = item
            current = current_by_code.get(code)
            matches[item.external_id] = current
            if current is None:
                additions['competences'].append(_entry(_competence_label(item), item.competence_type_name))
                continue
            details = []
            if normalize_text(current.name) != normalize_text(item.name):
                details.append(f'Название: "{current.name}" -> "{normalize_text(item.name)}"')
            if normalize_key(current.competence_type.name) != normalize_key(item.competence_type_name):
                details.append(f'Тип: "{current.competence_type.name}" -> "{normalize_text(item.competence_type_name)}"')
            if details:
                changes['competences'].append(_entry(_competence_label(current), *details))

        for code, current in current_by_code.items():
            if code not in incoming_by_code:
                missing['competences'].append(_entry(
                    _competence_label(current),
                    'Компетенция не будет удалена автоматически.',
                ))
        return matches

    @staticmethod
    def _preview_link_changes(
        dto: PlxProgramImportDTO,
        program: EducationalProgram,
        discipline_matches: dict[str, _DisciplineMatch],
        additions: dict[str, list[PreviewEntry]],
        missing: dict[str, list[PreviewEntry]],
        conflicts: list[ImportConflict],
    ) -> None:
        current_links = list(
            DisciplineCompetence.objects.filter(program_discipline__educational_program=program)
            .select_related('program_discipline__discipline', 'competence')
        )
        current_keys = {
            (('pd', str(link.program_discipline_id)), normalize_text(link.competence.code))
            for link in current_links
        }
        incoming_keys = set()

        competence_external_to_code = {
            item.external_id: normalize_text(item.code)
            for item in dto.competences
        }
        for link in dto.discipline_competence_links:
            discipline_match = discipline_matches.get(link.discipline_external_id)
            competence_code = competence_external_to_code.get(link.competence_external_id)
            if not discipline_match or not competence_code:
                continue
            if discipline_match.existing is not None:
                discipline_key = ('pd', str(discipline_match.existing.id))
            else:
                discipline_key = PlxProgramUpdateService._discipline_key_from_dto(discipline_match.incoming)
            key = (discipline_key, competence_code)
            incoming_keys.add(key)
            if key not in current_keys:
                additions['links'].append(_entry(
                    _discipline_label_from_dto(discipline_match.incoming),
                    f'Компетенция: {competence_code}',
                ))

        for link in current_links:
            key = (('pd', str(link.program_discipline_id)), normalize_text(link.competence.code))
            if key in incoming_keys:
                continue
            label = _discipline_label_from_model(link.program_discipline)
            missing['links'].append(_entry(
                label,
                f'Компетенция: {link.competence.code}',
                'Связь не будет удалена автоматически.',
            ))
            has_items = (
                AssessmentItem.objects.filter(
                    program_discipline=link.program_discipline,
                    competence=link.competence,
                ).exists()
                or AssessmentItemCompetence.objects.filter(
                    assessment_item__program_discipline=link.program_discipline,
                    competence=link.competence,
                ).exists()
            )
            if has_items:
                conflicts.append(ImportConflict(
                    label=f'{label} / {link.competence.code}',
                    message='Связь дисциплины с компетенцией отсутствует в новом PLX, но по ней есть задания.',
                    severity='warning',
                ))

    @staticmethod
    def _discipline_key_from_dto(item: DisciplineDTO) -> tuple[str, str]:
        code = normalize_text(item.code)
        if code:
            return 'code', code
        return 'name', normalize_key(item.name)

    def _apply_competences(
        self,
        dto: PlxProgramImportDTO,
        program: EducationalProgram,
        result: PlxUpdateResult,
    ) -> dict[str, Competence]:
        mapping: dict[str, Competence] = {}
        for item in dto.competences:
            code = normalize_text(item.code)
            if not code:
                continue
            competence_type = self._resolve_competence_type(item.competence_type_name)
            competence, created = Competence.objects.get_or_create(
                educational_program=program,
                code=code,
                defaults={
                    'competence_type': competence_type,
                    'name': normalize_text(item.name),
                },
            )
            if created:
                result.created_competences += 1
            else:
                fields_to_update = []
                if competence.name != normalize_text(item.name):
                    competence.name = normalize_text(item.name)
                    fields_to_update.append('name')
                if competence.competence_type_id != competence_type.id:
                    competence.competence_type = competence_type
                    fields_to_update.append('competence_type')
                if fields_to_update:
                    competence.save(update_fields=fields_to_update)
                    result.updated_competences += 1
            mapping[item.external_id] = competence
        return mapping

    @staticmethod
    def _apply_links(
        dto: PlxProgramImportDTO,
        discipline_map: dict[str, ProgramDiscipline],
        competence_map: dict[str, Competence],
    ) -> int:
        created = 0
        for item in dto.discipline_competence_links:
            program_discipline = discipline_map.get(item.discipline_external_id)
            competence = competence_map.get(item.competence_external_id)
            if not program_discipline or not competence:
                continue
            _, is_created = DisciplineCompetence.objects.get_or_create(
                program_discipline=program_discipline,
                competence=competence,
            )
            if is_created:
                created += 1
        return created

    @staticmethod
    def _resolve_competence_type(type_name: str) -> CompetenceType:
        clean_name = normalize_text(type_name).upper() or 'ПК'
        existing = CompetenceType.objects.filter(name__iexact=clean_name).first()
        if existing:
            return existing
        return CompetenceType.objects.create(name=clean_name)
