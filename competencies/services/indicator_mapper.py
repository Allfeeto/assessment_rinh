from __future__ import annotations

from dataclasses import dataclass

from competencies.models import Competence

from .exceptions import IndicatorIssue
from .indicator_parser import ParsedIndicatorRow, normalize_code


@dataclass(frozen=True, slots=True)
class MappedIndicatorRow:
    competence_id: int
    parsed: ParsedIndicatorRow


@dataclass(frozen=True, slots=True)
class IndicatorMappingResult:
    rows: list[MappedIndicatorRow]
    errors: list[IndicatorIssue]


class IndicatorMapper:
    """Сопоставляет коды только внутри явно выбранной образовательной программы."""

    def map_rows(self, rows: list[ParsedIndicatorRow], educational_program) -> IndicatorMappingResult:
        by_code: dict[str, list[Competence]] = {}
        for competence in Competence.objects.filter(educational_program=educational_program):
            by_code.setdefault(normalize_code(competence.code), []).append(competence)

        mapped = []
        errors = []
        for row in rows:
            code = normalize_code(row.competence_code)
            candidates = by_code.get(code, [])
            if not candidates:
                errors.append(self._issue(row, f'Компетенция {code} не найдена в выбранной программе.'))
                continue
            if len(candidates) > 1:
                errors.append(
                    self._issue(
                        row,
                        f'Код компетенции {code} неоднозначен после нормализации в выбранной программе.',
                    )
                )
                continue
            mapped.append(MappedIndicatorRow(competence_id=candidates[0].id, parsed=row))

        return IndicatorMappingResult(rows=mapped, errors=errors)

    @staticmethod
    def _issue(row: ParsedIndicatorRow, message: str) -> IndicatorIssue:
        return IndicatorIssue(
            severity='error',
            message=message,
            table_number=row.source_table_number,
            row_number=row.source_row_number,
            code=row.competence_code,
        )
