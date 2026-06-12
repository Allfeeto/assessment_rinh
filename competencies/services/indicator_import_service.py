from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from django.db import DatabaseError, transaction
from django.utils import timezone

from competencies.models import Competence, CompetenceIndicator, CompetenceIndicatorImport

from .exceptions import (
    IndicatorImportError,
    IndicatorIssue,
    IndicatorMappingError,
    IndicatorValidationError,
)
from .indicator_mapper import IndicatorMapper
from .indicator_document_converter import IndicatorDocumentConverter
from .indicator_parser import IndicatorDocxParser, normalize_code, normalize_text
from .indicator_validator import IndicatorValidator

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IndicatorImportResult:
    batch_id: int
    source_filename: str
    tables_found: int
    total_rows: int
    created_count: int
    updated_count: int
    skipped_count: int
    warning_count: int


class IndicatorImportService:
    def __init__(self):
        self.parser = IndicatorDocxParser()
        self.converter = IndicatorDocumentConverter()
        self.validator = IndicatorValidator()
        self.mapper = IndicatorMapper()

    def import_upload(self, uploaded_file, *, educational_program, user=None) -> IndicatorImportResult:
        filename, content = self.converter.read_upload(uploaded_file)
        batch = CompetenceIndicatorImport.objects.create(
            educational_program=educational_program,
            uploaded_by=self._user_or_none(user),
            source_filename=filename,
            source_sha256=hashlib.sha256(content).hexdigest(),
            status=CompetenceIndicatorImport.Status.PROCESSING,
        )

        try:
            prepared = self.converter.prepare_content(source_filename=filename, content=content)
            parsed = self.parser.parse_bytes(content=prepared.docx_content, source_filename=filename)
            batch.total_rows = len(parsed.rows)
            validation = self.validator.validate(parsed)
            mapping = self.mapper.map_rows(validation.rows, educational_program)
            errors = [*validation.errors, *mapping.errors]
            warnings = validation.warnings
            if errors:
                raise IndicatorMappingError(
                    'Импорт отменён: исправьте ошибки сопоставления и повторите загрузку.',
                    issues=errors,
                    batch_id=batch.id,
                )

            with transaction.atomic():
                created_count, updated_count, skipped_count = self._persist(
                    batch=batch,
                    mapped_rows=mapping.rows,
                )
                self._complete_batch(
                    batch,
                    total_rows=len(parsed.rows),
                    created_count=created_count,
                    updated_count=updated_count,
                    skipped_count=skipped_count + len(warnings) + parsed.skipped_rows,
                    warnings=warnings,
                )
            logger.info(
                'Competence indicator import completed: batch_id=%s program_id=%s created=%s updated=%s skipped=%s',
                batch.id,
                educational_program.id,
                created_count,
                updated_count,
                skipped_count,
            )
            return IndicatorImportResult(
                batch_id=batch.id,
                source_filename=filename,
                tables_found=parsed.tables_found,
                total_rows=len(parsed.rows),
                created_count=created_count,
                updated_count=updated_count,
                skipped_count=skipped_count + len(warnings) + parsed.skipped_rows,
                warning_count=len(warnings),
            )
        except IndicatorImportError as exc:
            issues = exc.issues or [IndicatorIssue(severity='error', message=str(exc))]
            self._fail_batch(batch, issues)
            exc.issues = issues
            exc.batch_id = batch.id
            raise
        except DatabaseError as exc:
            logger.exception('Database error during competence indicator import: batch_id=%s', batch.id)
            issue = IndicatorIssue(severity='error', message='Ошибка базы данных при сохранении индикаторов.')
            self._fail_batch(batch, [issue])
            raise IndicatorImportError(
                'Не удалось сохранить индикаторы. Изменения отменены.',
                issues=[issue],
                batch_id=batch.id,
            ) from exc
        except Exception as exc:
            logger.exception('Unexpected competence indicator import error: batch_id=%s', batch.id)
            issue = IndicatorIssue(severity='error', message='Непредвиденная ошибка обработки Word-файла.')
            self._fail_batch(batch, [issue])
            raise IndicatorImportError(
                'Не удалось обработать файл индикаторов.',
                issues=[issue],
                batch_id=batch.id,
            ) from exc

    @staticmethod
    def _user_or_none(user):
        if user is not None and getattr(user, 'is_authenticated', False):
            return user
        return None

    def _persist(self, *, batch, mapped_rows):
        competence_ids = {row.competence_id for row in mapped_rows}
        list(
            Competence.objects.select_for_update()
            .filter(id__in=competence_ids)
            .values_list('id', flat=True)
        )

        codes = {normalize_code(row.parsed.indicator_code) for row in mapped_rows}
        existing = {
            (item.competence_id, normalize_code(item.code)): item
            for item in CompetenceIndicator.objects.select_for_update().filter(
                competence_id__in=competence_ids,
                code__in=codes,
            )
        }

        now = timezone.now()
        to_create = []
        to_update = []
        skipped_count = 0
        for mapped in mapped_rows:
            row = mapped.parsed
            code = normalize_code(row.indicator_code)
            text = normalize_text(row.text)
            current = existing.get((mapped.competence_id, code))
            if current is None:
                to_create.append(
                    CompetenceIndicator(
                        competence_id=mapped.competence_id,
                        last_import=batch,
                        code=code,
                        text=text,
                        source_file=batch.source_filename,
                        source_table_number=row.source_table_number,
                        source_row_number=row.source_row_number,
                    )
                )
                continue
            if normalize_text(current.text) == text:
                skipped_count += 1
                continue

            current.text = text
            current.last_import = batch
            current.source_file = batch.source_filename
            current.source_table_number = row.source_table_number
            current.source_row_number = row.source_row_number
            current.updated_at = now
            to_update.append(current)

        if to_create:
            CompetenceIndicator.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            CompetenceIndicator.objects.bulk_update(
                to_update,
                fields=(
                    'text',
                    'last_import',
                    'source_file',
                    'source_table_number',
                    'source_row_number',
                    'updated_at',
                ),
                batch_size=500,
            )
        return len(to_create), len(to_update), skipped_count

    @staticmethod
    def _complete_batch(
        batch,
        *,
        total_rows,
        created_count,
        updated_count,
        skipped_count,
        warnings,
    ):
        batch.status = CompetenceIndicatorImport.Status.COMPLETED
        batch.total_rows = total_rows
        batch.created_count = created_count
        batch.updated_count = updated_count
        batch.skipped_count = skipped_count
        batch.warning_count = len(warnings)
        batch.error_count = 0
        batch.error_summary = IndicatorImportService._format_issues(warnings) or None
        batch.completed_at = timezone.now()
        batch.save(
            update_fields=(
                'status',
                'total_rows',
                'created_count',
                'updated_count',
                'skipped_count',
                'warning_count',
                'error_count',
                'error_summary',
                'completed_at',
            )
        )

    @staticmethod
    def _fail_batch(batch, issues):
        batch.status = CompetenceIndicatorImport.Status.FAILED
        batch.error_count = sum(issue.severity == 'error' for issue in issues)
        batch.warning_count = sum(issue.severity == 'warning' for issue in issues)
        batch.error_summary = IndicatorImportService._format_issues(issues) or 'Импорт завершился ошибкой.'
        batch.completed_at = timezone.now()
        batch.save(
            update_fields=(
                'status',
                'total_rows',
                'error_count',
                'warning_count',
                'error_summary',
                'completed_at',
            )
        )

    @staticmethod
    def _format_issues(issues) -> str:
        return '\n'.join(issue.display() for issue in issues[:100])
