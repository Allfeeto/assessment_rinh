from datetime import timedelta

from django.utils import timezone

from programs.models import ProgramPlxImportDraft

from .plx_dto import PlxProgramImportDTO


class PlxImportDraftService:
    lifetime = timedelta(hours=24)

    def create(self, *, dto, user, existing_program=None):
        self.cleanup_expired()
        return ProgramPlxImportDraft.objects.create(
            uploaded_by=user,
            existing_program=existing_program,
            source_filename=dto.source_filename,
            dto_payload=dto.to_dict(),
            expires_at=timezone.now() + self.lifetime,
        )

    def get_for_user(self, draft_id, user):
        if not draft_id:
            return None
        try:
            normalized_id = int(draft_id)
        except (TypeError, ValueError):
            return None
        draft = (
            ProgramPlxImportDraft.objects.select_related(
                'existing_program__program_profile__training_direction__education_level',
                'existing_program__department',
            )
            .filter(
                pk=normalized_id,
                uploaded_by=user,
                expires_at__gt=timezone.now(),
            )
            .first()
        )
        return draft

    @staticmethod
    def dto_from_draft(draft):
        return PlxProgramImportDTO.from_dict(draft.dto_payload)

    @staticmethod
    def delete(draft):
        if draft is not None:
            draft.delete()

    @staticmethod
    def cleanup_expired():
        ProgramPlxImportDraft.objects.filter(expires_at__lte=timezone.now()).delete()
