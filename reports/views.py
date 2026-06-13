from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from core.view_helpers import FragmentTemplateMixin

from .forms import ReportFilterForm
from .selectors import build_reports_dashboard_context


class ReportsDashboardView(LoginRequiredMixin, FragmentTemplateMixin, TemplateView):
    template_name = 'reports/report.html'
    fragment_templates = {
        'competence_coverage': 'reports/includes/competence_coverage_table.html',
        'discipline_competence': 'reports/includes/discipline_competence_table.html',
        'report_by_type': 'reports/includes/report_by_type_table.html',
        'report_by_program': 'reports/includes/report_by_program_table.html',
        'report_by_discipline': 'reports/includes/report_by_discipline_table.html',
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = ReportFilterForm(self.request.GET or None, user=self.request.user)
        context['form'] = form
        context.update(
            build_reports_dashboard_context(
                self.request,
                form,
                fragment=self.get_requested_fragment(),
            )
        )
        return context
