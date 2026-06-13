from __future__ import annotations

from dataclasses import dataclass

from .exceptions import IndicatorIssue
from .indicator_parser import ParsedIndicatorDocument, ParsedIndicatorRow, normalize_code, normalize_text

EXPECTED_INDICATOR_ROLES = {
    '1': 'Знает',
    '2': 'Умеет',
    '3': 'Владеет',
}


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

        errors.extend(self._validate_competence_indicator_sets(unique_rows))
        return IndicatorValidationResult(rows=unique_rows, errors=errors, warnings=warnings)

    def _validate_competence_indicator_sets(
        self,
        rows: list[ParsedIndicatorRow],
    ) -> list[IndicatorIssue]:
        grouped: dict[str, list[ParsedIndicatorRow]] = {}
        for row in rows:
            grouped.setdefault(normalize_code(row.competence_code), []).append(row)

        errors = []
        for competence_code, competence_rows in grouped.items():
            expected_codes = {
                f'{competence_code}.{suffix}'
                for suffix in EXPECTED_INDICATOR_ROLES
            }
            actual_codes = {
                normalize_code(row.indicator_code)
                for row in competence_rows
            }
            if actual_codes != expected_codes:
                missing = sorted(expected_codes - actual_codes)
                unexpected = sorted(actual_codes - expected_codes)
                details = []
                if missing:
                    details.append(f'отсутствуют: {", ".join(missing)}')
                if unexpected:
                    details.append(f'лишние: {", ".join(unexpected)}')
                errors.append(
                    self._issue(
                        competence_rows[0],
                        (
                            f'Для компетенции {competence_code} должен быть полный набор '
                            f'из трёх индикаторов .1, .2, .3 '
                            f'({"; ".join(details)}).'
                        ),
                    )
                )

            for row in competence_rows:
                indicator_code = normalize_code(row.indicator_code)
                suffix = indicator_code.rsplit('.', 1)[-1] if '.' in indicator_code else ''
                expected_role = EXPECTED_INDICATOR_ROLES.get(suffix)
                if expected_role and not normalize_text(row.text).casefold().startswith(
                    expected_role.casefold()
                ):
                    errors.append(
                        self._issue(
                            row,
                            f'Индикатор {indicator_code} должен начинаться со слова «{expected_role}».',
                        )
                    )
        return errors

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
