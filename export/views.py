from django.http import HttpResponse, JsonResponse
from django.views import View

from .forms import WordExportForm
from .services import generate_docx


class WordExportView(View):
    def get(self, request, *args, **kwargs):
        form = WordExportForm(request.GET)
        if not form.is_valid():
            return JsonResponse({'errors': form.errors}, status=400)

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
            return JsonResponse({'errors': str(error)}, status=404)

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