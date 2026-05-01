from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import IntegrityError, transaction

from competencies.models import Competence, DisciplineCompetence
from core.models import CompetenceType, EducationLevel
from disciplines.models import Discipline, ProgramDiscipline
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection
from teachers.models import Department

from .exceptions import PlxConflictError, PlxImportError, PlxValidationError
from .plx_dto import PlxProgramImportDTO
from .plx_mapping import normalize_key, normalize_text, PlxMapper
from .plx_parser import PlxParser
from .program_trash_service import ProgramTrashService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ImportResult:
    created_program_id: int
    replaced_program_id: int | None
    disciplines_count: int
    competences_count: int
    links_count: int


class PlxImportService:
    def __init__(self):
        self.parser = PlxParser()
        self.mapper = PlxMapper()
        self.trash_service = ProgramTrashService()

    def build_dto_from_upload(self, uploaded_file) -> PlxProgramImportDTO:
        parsed = self.parser.parse_upload(uploaded_file)
        return self.mapper.map_to_dto(parsed)

    def find_existing_program(self, dto: PlxProgramImportDTO) -> EducationalProgram | None:
        profile = ProgramProfile.objects.filter(code__iexact=dto.program.profile_code).first()
        if profile is None:
            return None

        department = Department.objects.filter(number=dto.department.number).first()
        if department is None:
            return None

        return EducationalProgram.objects.active().filter(
            program_profile=profile,
            department=department,
            admission_year=dto.program.admission_year,
        ).first()

    def import_program(self, dto: PlxProgramImportDTO, *, replace_existing: bool, user=None) -> ImportResult:
        with transaction.atomic():
            education_level = self._resolve_education_level(dto.program.education_level_name)
            direction = self._resolve_training_direction(
                code=dto.program.training_direction_code,
                name=dto.program.training_direction_name,
                education_level=education_level,
            )
            profile = self._resolve_program_profile(
                code=dto.program.profile_code,
                name=dto.program.profile_name,
                training_direction=direction,
            )
            department = self._resolve_department(dto.department.number, dto.department.short_name, dto.department.full_name)

            existing_program = EducationalProgram.objects.active().filter(
                program_profile=profile,
                department=department,
                admission_year=dto.program.admission_year,
            ).first()

            replaced_program_id = None
            if existing_program and not replace_existing:
                raise PlxConflictError(
                    'Такая образовательная программа уже существует. '
                    'Подтвердите замену, чтобы переместить старую версию в корзину и загрузить новую.',
                    existing_program_id=existing_program.id,
                )
            if existing_program and replace_existing:
                replaced_program_id = existing_program.id
                self.trash_service.move_to_trash(
                    existing_program,
                    user=user,
                    reason='Замена образовательной программы через импорт PLX',
                )

            program = EducationalProgram.objects.create(
                program_profile=profile,
                department=department,
                admission_year=dto.program.admission_year,
            )

            discipline_map = self._import_disciplines(dto, program)
            competence_map = self._import_competences(dto, program)
            links_count = self._import_discipline_competence_links(
                dto,
                discipline_map=discipline_map,
                competence_map=competence_map,
            )

            logger.info(
                'PLX import completed: program_id=%s replaced_program_id=%s disciplines=%s competences=%s links=%s',
                program.id,
                replaced_program_id,
                len(discipline_map),
                len(competence_map),
                links_count,
            )

            return ImportResult(
                created_program_id=program.id,
                replaced_program_id=replaced_program_id,
                disciplines_count=len(discipline_map),
                competences_count=len(competence_map),
                links_count=links_count,
            )

    def _resolve_education_level(self, source_name: str) -> EducationLevel:
        normalized = normalize_key(source_name)
        if not normalized:
            raise PlxValidationError('Не удалось определить уровень образования.')

        levels = list(EducationLevel.objects.all())
        for item in levels:
            if normalize_key(item.name) == normalized:
                return item

        for item in levels:
            name_key = normalize_key(item.name)
            if ('бакалавр' in normalized and 'бакалавр' in name_key) or (
                'магист' in normalized and 'магист' in name_key
            ) or ('специал' in normalized and 'специал' in name_key):
                return item

        return EducationLevel.objects.create(name=normalize_text(source_name))

    @staticmethod
    def _resolve_training_direction(
        *,
        code: str,
        name: str,
        education_level: EducationLevel,
    ) -> TrainingDirection:
        code = normalize_text(code)
        name = normalize_text(name)
        if not code or not name:
            raise PlxValidationError('Некорректные данные направления подготовки в PLX.')

        direction = TrainingDirection.objects.filter(code=code).first()
        if direction is None:
            return TrainingDirection.objects.create(
                education_level=education_level,
                code=code,
                name=name,
            )

        fields_to_update: list[str] = []
        if direction.name != name:
            direction.name = name
            fields_to_update.append('name')
        if direction.education_level_id != education_level.id:
            direction.education_level = education_level
            fields_to_update.append('education_level')
        if fields_to_update:
            direction.save(update_fields=fields_to_update)
        return direction

    @staticmethod
    def _resolve_program_profile(
        *,
        code: str,
        name: str,
        training_direction: TrainingDirection,
    ) -> ProgramProfile:
        code = normalize_text(code)
        name = normalize_text(name)
        if not code or not name:
            raise PlxValidationError('Некорректные данные профиля программы в PLX.')

        profile = ProgramProfile.objects.filter(code__iexact=code).first()
        if profile is None:
            return ProgramProfile.objects.create(
                training_direction=training_direction,
                code=code,
                name=name,
            )

        fields_to_update: list[str] = []
        if profile.name != name:
            profile.name = name
            fields_to_update.append('name')
        if profile.training_direction_id != training_direction.id:
            profile.training_direction = training_direction
            fields_to_update.append('training_direction')
        if fields_to_update:
            profile.save(update_fields=fields_to_update)
        return profile

    @staticmethod
    def _resolve_department(number: str, short_name: str, full_name: str) -> Department:
        number = normalize_text(number)
        short_name = normalize_text(short_name)
        full_name = normalize_text(full_name)
        if not number or not short_name or not full_name:
            raise PlxValidationError('Некорректные данные кафедры в PLX.')

        department = Department.objects.filter(number=number).first()
        if department is None:
            return Department.objects.create(
                number=number,
                short_name=short_name,
                full_name=full_name,
                head_teacher=None,
            )

        fields_to_update: list[str] = []
        if department.short_name != short_name:
            department.short_name = short_name
            fields_to_update.append('short_name')
        if department.full_name != full_name:
            department.full_name = full_name
            fields_to_update.append('full_name')
        if fields_to_update:
            department.save(update_fields=fields_to_update)
        return department

    def _resolve_discipline(self, name: str) -> Discipline:
        clean_name = normalize_text(name)
        if not clean_name:
            raise PlxValidationError('Обнаружено пустое название дисциплины в PLX.')

        existing = Discipline.objects.filter(name__iexact=clean_name).first()
        if existing:
            return existing
        return Discipline.objects.create(name=clean_name)

    def _resolve_competence_type(self, type_name: str) -> CompetenceType:
        clean_name = normalize_text(type_name).upper()
        if not clean_name:
            clean_name = 'ПК'

        existing = CompetenceType.objects.filter(name__iexact=clean_name).first()
        if existing:
            return existing
        return CompetenceType.objects.create(name=clean_name)

    def _import_disciplines(
        self,
        dto: PlxProgramImportDTO,
        program: EducationalProgram,
    ) -> dict[str, ProgramDiscipline]:
        mapping: dict[str, ProgramDiscipline] = {}
        for item in dto.disciplines:
            discipline = self._resolve_discipline(item.name)
            program_discipline, _ = ProgramDiscipline.objects.get_or_create(
                educational_program=program,
                discipline=discipline,
            )
            mapping[item.external_id] = program_discipline
        return mapping

    def _import_competences(
        self,
        dto: PlxProgramImportDTO,
        program: EducationalProgram,
    ) -> dict[str, Competence]:
        mapping: dict[str, Competence] = {}
        for item in dto.competences:
            competence_type = self._resolve_competence_type(item.competence_type_name)
            try:
                competence = Competence.objects.create(
                    educational_program=program,
                    competence_type=competence_type,
                    code=normalize_text(item.code),
                    name=normalize_text(item.name),
                )
            except IntegrityError as exc:
                raise PlxImportError(
                    f'Не удалось создать компетенцию "{item.code}". Проверьте корректность данных PLX.'
                ) from exc
            mapping[item.external_id] = competence
        return mapping

    @staticmethod
    def _import_discipline_competence_links(
        dto: PlxProgramImportDTO,
        *,
        discipline_map: dict[str, ProgramDiscipline],
        competence_map: dict[str, Competence],
    ) -> int:
        created = 0
        for link in dto.discipline_competence_links:
            program_discipline = discipline_map.get(link.discipline_external_id)
            competence = competence_map.get(link.competence_external_id)
            if not program_discipline or not competence:
                continue

            _, is_created = DisciplineCompetence.objects.get_or_create(
                program_discipline=program_discipline,
                competence=competence,
            )
            if is_created:
                created += 1
        return created
