import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.http import content_disposition_header
from django.views import View

from assessment.access import can_access_program_discipline
from disciplines.models import ProgramDiscipline

from .forms import WordExportForm
from .services import WordExportError, build_export_filename, generate_docx


logger = logging.getLogger(__name__)


class WordExportView(LoginRequiredMixin, View):
    template_name = 'export/word.html'

    def get(self, request, *args, **kwargs):
        has_params = bool(request.GET)
        wants_download = request.GET.get('download') == '1'
        form = WordExportForm(
            request.GET if has_params else None,
            validate_required=wants_download,
            user=request.user,
        )

        if not wants_download:
            return render(request, self.template_name, {'form': form})

        if not form.is_valid():
            return render(request, self.template_name, {'form': form}, status=400)

        educational_program = form.cleaned_data['educational_program']
        discipline = form.cleaned_data['discipline']
        assessment_item_type = form.cleaned_data.get('assessment_item_type')
        competence = form.cleaned_data.get('competence')

        program_discipline = (
            ProgramDiscipline.objects.filter(
                educational_program_id=educational_program.id,
                discipline_id=discipline.id,
                educational_program__is_deleted=False,
            )
            .first()
        )
        if not program_discipline:
            form.add_error('discipline', 'Выбранная дисциплина не включена в указанную образовательную программу.')
            return render(request, self.template_name, {'form': form}, status=404)

        program_discipline_id = getattr(program_discipline, 'id', program_discipline)
        if not can_access_program_discipline(request.user, program_discipline_id):
            raise PermissionDenied('У вас нет доступа к экспорту материалов по выбранной дисциплине.')

        try:
            content = generate_docx(
                program_id=educational_program.id,
                discipline_id=discipline.id,
                filters={
                    'assessment_item_type_id': assessment_item_type.id if assessment_item_type else None,
                    'competence_id': competence.id if competence else None,
                },
            )
        except WordExportError as exc:
            form.add_error(None, str(exc))
            return render(request, self.template_name, {'form': form}, status=exc.status_code)

        logger.info(
            'Word export generated',
            extra={
                'user_id': request.user.id,
                'program_id': educational_program.id,
                'discipline_id': discipline.id,
                'program_discipline_id': program_discipline_id,
                'assessment_item_type_id': assessment_item_type.id if assessment_item_type else None,
                'competence_id': competence.id if competence else None,
            },
        )

        filename = build_export_filename(educational_program, discipline, program_discipline)
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response['Content-Disposition'] = content_disposition_header(True, filename)
        return response
