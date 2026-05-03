from __future__ import annotations

from .curriculum_replacement_service import CurriculumReplacementService
from .program_trash_service import ProgramTrashService


class ProgramReplaceService:
    """
    Совместимый фасад для старого имени сервиса.

    Замена через импорт больше не должна физически удалять программу: для этого
    используется move_to_trash. Физическое удаление оставлено только как явная
    операция над программой, уже находящейся в корзине.
    """

    def __init__(self):
        self.replacement_service = CurriculumReplacementService()
        self.trash_service = ProgramTrashService()

    def move_to_trash(self, educational_program, *, user=None, reason=None):
        return self.trash_service.move_to_trash(
            educational_program,
            user=user,
            reason=reason,
        )

    def replace_for_plx_import(self, educational_program, *, user=None):
        return self.replacement_service.replace_for_plx_import(
            educational_program,
            user=user,
        )

    def delete_program_with_dependencies(self, educational_program) -> None:
        self.trash_service.hard_delete(educational_program)
