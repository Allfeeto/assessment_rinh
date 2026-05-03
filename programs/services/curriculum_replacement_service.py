from __future__ import annotations

import logging
from dataclasses import dataclass

from .program_trash_service import ProgramTrashService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CurriculumReplacementPolicy:
    action: str = 'move_existing_program_to_trash'
    destructive: bool = False
    preserves: tuple[str, ...] = (
        'program_disciplines',
        'competences',
        'discipline_competences',
        'assessment_items',
        'assessment_item_rows',
        'assessment_item_competences',
        'teacher_assignments',
    )
    hard_delete_requires_trash: bool = True


class CurriculumReplacementService:
    """
    Application service for replacing a curriculum imported from PLX.

    Replacement is intentionally non-destructive: the old active program is
    moved to trash with its owned domain data preserved. Hard deletion is a
    separate staff action against an already trashed program.
    """

    policy = CurriculumReplacementPolicy()

    def __init__(self, *, trash_service: ProgramTrashService | None = None):
        self.trash_service = trash_service or ProgramTrashService()

    def replace_for_plx_import(self, educational_program, *, user=None):
        logger.info(
            'Curriculum replacement policy applied',
            extra={
                'program_id': educational_program.id,
                'action': self.policy.action,
                'destructive': self.policy.destructive,
                'preserves': self.policy.preserves,
            },
        )
        return self.trash_service.move_to_trash(
            educational_program,
            user=user,
            reason='Замена образовательной программы через импорт PLX',
        )
