from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from assessment.access import can_access_program_discipline
from disciplines.models import ProgramDiscipline

from .forms import WordExportForm
from .services import generate_docx


class WordExportView(LoginRequiredMixin, View):
    template_name = 'export/word.html'

    def get(self, request, *args, **kwargs):
        has_params = bool(request.GET.get('educational_program') or request.GET.get('discipline'))
        form = WordExportForm(request.GET if has_params else None)

        if not has_params:
            return render(request, self.template_name, {'form': form})

        if not form.is_valid():
            return render(request, self.template_name, {'form': form}, status=400)

        educational_program = form.cleaned_data['educational_program']
        discipline = form.cleaned_data['discipline']
        assessment_item_type = form.cleaned_data.get('assessment_item_type')
        competence = form.cleaned_data.get('competence')

        program_discipline_id = (
            ProgramDiscipline.objects.filter(
                educational_program_id=educational_program.id,
                discipline_id=discipline.id,
            )
            .values_list('id', flat=True)
            .first()
        )
        if not program_discipline_id:
            form.add_error('discipline', 'Выбранная дисциплина не включена в указанную образовательную программу.')
            return render(request, self.template_name, {'form': form}, status=404)

        if not can_access_program_discipline(request.user, program_discipline_id, allow_staff=True):
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
        except ValueError as exc:
            form.add_error(None, str(exc))
            return render(request, self.template_name, {'form': form}, status=404)

        filename = (
            f'assessment_program_{educational_program.id}_discipline_{discipline.id}.docx'
        )
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
