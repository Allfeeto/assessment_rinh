from django.shortcuts import render
from django.http import HttpResponse
from django.views import View

from assessment.models import AssessmentItemType
from competencies.models import Competence
from core.models import EducationalProgram
from disciplines.models import Discipline

from .forms import WordExportForm
from .services import generate_docx


class WordExportView(View):
    template_name = 'export/word.html'

    @staticmethod
    def _build_context(form):
        return {
            'form': form,
            'programs': EducationalProgram.objects.order_by('code'),
            'disciplines': Discipline.objects.order_by('name'),
            'assessment_item_types': AssessmentItemType.objects.order_by('name'),
            'competences': Competence.objects.order_by('code'),
        }

    def get(self, request, *args, **kwargs):
        has_export_params = bool(request.GET.get('program_id') or request.GET.get('discipline_id'))
        form = WordExportForm(request.GET if has_export_params else None)

        if not has_export_params:
            return render(request, self.template_name, self._build_context(form))

        if not form.is_valid():
            return render(request, self.template_name, self._build_context(form), status=400)

        payload = form.cleaned_data
        filters = {
            'assessment_item_type': payload.get('assessment_item_type'),
            'competence': payload.get('competence'),
        }

        try:
            content = generate_docx(
                program_id=payload['program_id'],
                discipline_id=payload['discipline_id'],
                filters=filters,
            )
        except ValueError as error:
            form.add_error(None, str(error))
            return render(request, self.template_name, self._build_context(form), status=404)

        filename = (
            f"assessment_program_{payload['program_id']}"
            f"_discipline_{payload['discipline_id']}.docx"
        )

        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
