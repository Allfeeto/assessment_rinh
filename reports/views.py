from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .forms import ReportFilterForm
from .selectors import build_reports_dashboard_context


class ReportsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = ReportFilterForm(self.request.GET or None, user=self.request.user)
        context['form'] = form
        context.update(build_reports_dashboard_context(self.request, form))
        return context
