from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView


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


class NamedListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy('login')
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
        context['create_url_name'] = self.create_url_name
        context['detail_url_name'] = self.detail_url_name
        context['update_url_name'] = self.update_url_name
        context['delete_url_name'] = self.delete_url_name
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


class NamedDetailView(LoginRequiredMixin, DetailView):
    login_url = reverse_lazy('login')
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
        context['update_url_name'] = self.update_url_name
        context['delete_url_name'] = self.delete_url_name
        context['display_fields'] = [
            (label, resolve_attr(self.object, attr_path)) for label, attr_path in self.detail_fields
        ]
        return context


class NamedCreateView(LoginRequiredMixin, CreateView):
    login_url = reverse_lazy('login')
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


class NamedUpdateView(LoginRequiredMixin, UpdateView):
    login_url = reverse_lazy('login')
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


class NamedDeleteView(LoginRequiredMixin, DeleteView):
    login_url = reverse_lazy('login')
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
