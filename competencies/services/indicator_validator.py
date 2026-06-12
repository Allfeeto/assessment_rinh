from __future__ import annotations

from dataclasses import dataclass

from .exceptions import IndicatorIssue
from .indicator_parser import ParsedIndicatorDocument, ParsedIndicatorRow, normalize_code, normalize_text


@dataclass(frozen=True, slots=True)
class IndicatorValidationResult:
    rows: list[ParsedIndicatorRow]
    errors: list[IndicatorIssue]
    warnings: list[IndicatorIssue]


class IndicatorValidator:
    def validate(self, parsed: ParsedIndicatorDocument) -> IndicatorValidationResult:
        errors: list[IndicatorIssue] = []
        warnings: list[IndicatorIssue] = []
        unique_rows: list[ParsedIndicatorRow] = []
        seen: dict[str, ParsedIndicatorRow] = {}

        for row in parsed.rows:
            row_errors = self._validate_row(row)
            errors.extend(row_errors)
            if row_errors:
                continue

            key = normalize_code(row.indicator_code)
            previous = seen.get(key)
            if previous is not None:
                if normalize_text(previous.text).casefold() == normalize_text(row.text).casefold():
                    warnings.append(
                        self._issue(
                            row,
                            f'Дубликат индикатора {key} в файле пропущен.',
                            severity='warning',
                        )
                    )
                else:
                    errors.append(
                        self._issue(
                            row,
                            f'Код индикатора {key} встречается в файле с разными текстами.',
                        )
                    )
                continue

            seen[key] = row
            unique_rows.append(row)

        return IndicatorValidationResult(rows=unique_rows, errors=errors, warnings=warnings)

    def _validate_row(self, row: ParsedIndicatorRow) -> list[IndicatorIssue]:
        errors = []
        if not normalize_code(row.competence_code):
            errors.append(self._issue(row, 'Не найден код компетенции.'))
        if not normalize_code(row.indicator_code):
            errors.append(self._issue(row, 'Не найден код индикатора.'))
        if not normalize_text(row.text):
            errors.append(self._issue(row, 'Текст индикатора пуст.'))

        competence_code = normalize_code(row.competence_code)
        indicator_code = normalize_code(row.indicator_code)
        indicator_competence_code = indicator_code.rsplit('.', 1)[0] if '.' in indicator_code else ''
        if competence_code and indicator_competence_code and competence_code != indicator_competence_code:
            errors.append(
                self._issue(
                    row,
                    f'Индикатор {indicator_code} не относится к компетенции {competence_code}.',
                )
            )
        return errors

    @staticmethod
    def _issue(row: ParsedIndicatorRow, message: str, *, severity: str = 'error') -> IndicatorIssue:
        return IndicatorIssue(
            severity=severity,
            message=message,
            table_number=row.source_table_number,
            row_number=row.source_row_number,
            code=row.indicator_code or row.competence_code,
        )
