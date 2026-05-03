from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .permissions import can_use_model_permission, is_staff_or_superuser


PER_PAGE_CHOICES = (50, 100, 200)
DEFAULT_PER_PAGE = 50


def get_per_page(request, *, default=DEFAULT_PER_PAGE, choices=PER_PAGE_CHOICES):
    raw_per_page = (request.GET.get('per_page') or '').strip()
    if raw_per_page.isdigit():
        per_page = int(raw_per_page)
        if per_page in choices:
            return per_page
    return default


def paginate_queryset(request, queryset, *, page_param='page', per_page=None):
    page_size = per_page or get_per_page(request)
    paginator = Paginator(queryset, page_size)
    return paginator.get_page(request.GET.get(page_param) or 1)


def query_params_without(request, *keys):
    params = request.GET.copy()
    for key in keys:
        params.pop(key, None)
    return params.urlencode()


def resolve_attr(obj, path):
    value = obj
    for part in path.split('.'):
        value = getattr(value, part, None)
        if value is None:
            return ''
    return value


class StaffOrModelPermissionRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    login_url = reverse_lazy('login')
    raise_exception = True
    permission_action = None

    def get_permission_model(self):
        model = getattr(self, 'model', None)
        if model is not None:
            return model
        queryset = getattr(self, 'queryset', None)
        if queryset is not None:
            return queryset.model
        return None

    def get_permission_required(self):
        if self.permission_required:
            return super().get_permission_required()

        model = self.get_permission_model()
        if model is None or not self.permission_action:
            return ()

        opts = model._meta
        return (f'{opts.app_label}.{self.permission_action}_{opts.model_name}',)

    def has_permission(self):
        return is_staff_or_superuser(self.request.user)

    def can_use_action(self, action):
        model = self.get_permission_model()
        if model is None:
            return True
        return can_use_model_permission(self.request.user, model, action)


class NamedListView(StaffOrModelPermissionRequiredMixin, ListView):
    login_url = reverse_lazy('login')
    permission_action = 'view'
    template_name = 'common/list.html'
    context_object_name = 'objects'
    paginate_by = DEFAULT_PER_PAGE
    per_page_choices = PER_PAGE_CHOICES
    title = ''
    search_fields = ()
    list_columns = ()
    order_by = ('id',)
    create_url_name = ''
    detail_url_name = ''
    update_url_name = ''
    delete_url_name = ''

    def get_queryset(self):
        queryset = super().get_queryset().order_by(*self.order_by)
        query = self.request.GET.get('q', '').strip()
        if query and self.search_fields:
            conditions = Q()
            for field in self.search_fields:
                conditions |= Q(**{f'{field}__icontains': query})
            queryset = queryset.filter(conditions)
        return queryset

    def get_paginate_by(self, queryset):
        return get_per_page(
            self.request,
            default=self.paginate_by,
            choices=self.per_page_choices,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['search_query'] = self.request.GET.get('q', '')
        context['list_columns'] = self.list_columns
        can_view_detail = bool(self.detail_url_name)
        can_change = self.can_use_action('change')
        can_delete = self.can_use_action('delete')
        context['create_url_name'] = self.create_url_name if self.can_use_action('add') else ''
        context['detail_url_name'] = self.detail_url_name
        context['update_url_name'] = self.update_url_name if can_change else ''
        context['delete_url_name'] = self.delete_url_name if can_delete else ''
        context['has_row_actions'] = can_view_detail or can_change or can_delete
        context['per_page_choices'] = self.per_page_choices
        context['selected_per_page'] = self.get_paginate_by(context.get('object_list'))

        rows = []
        for obj in context['object_list']:
            rows.append(
                {
                    'object': obj,
                    'values': [resolve_attr(obj, column_path) for _, column_path in self.list_columns],
                }
            )
        context['rows'] = rows

        context['query_params'] = query_params_without(self.request, 'page')
        return context


class NamedDetailView(StaffOrModelPermissionRequiredMixin, DetailView):
    login_url = reverse_lazy('login')
    permission_action = 'view'
    template_name = 'common/detail.html'
    title = ''
    list_url_name = ''
    update_url_name = ''
    delete_url_name = ''
    detail_fields = ()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['list_url_name'] = self.list_url_name
        context['update_url_name'] = self.update_url_name if self.can_use_action('change') else ''
        context['delete_url_name'] = self.delete_url_name if self.can_use_action('delete') else ''
        context['display_fields'] = [
            (label, resolve_attr(self.object, attr_path)) for label, attr_path in self.detail_fields
        ]
        return context


class NamedCreateView(StaffOrModelPermissionRequiredMixin, CreateView):
    login_url = reverse_lazy('login')
    permission_action = 'add'
    template_name = 'common/form.html'
    title = ''
    list_url_name = ''

    def get_success_url(self):
        return reverse_lazy(self.list_url_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['list_url_name'] = self.list_url_name
        context['submit_text'] = 'Сохранить'
        return context


class NamedUpdateView(StaffOrModelPermissionRequiredMixin, UpdateView):
    login_url = reverse_lazy('login')
    permission_action = 'change'
    template_name = 'common/form.html'
    title = ''
    list_url_name = ''

    def get_success_url(self):
        return reverse_lazy(self.list_url_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['list_url_name'] = self.list_url_name
        context['submit_text'] = 'Сохранить изменения'
        return context


class NamedDeleteView(StaffOrModelPermissionRequiredMixin, DeleteView):
    login_url = reverse_lazy('login')
    permission_action = 'delete'
    template_name = 'common/confirm_delete.html'
    title = ''
    list_url_name = ''

    def get_success_url(self):
        return reverse_lazy(self.list_url_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['list_url_name'] = self.list_url_name
        return context
