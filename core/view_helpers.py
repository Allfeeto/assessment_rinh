from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView


def resolve_attr(obj, path):
    value = obj
    for part in path.split('.'):
        value = getattr(value, part, None)
        if value is None:
            return ''
    return value


class NamedListView(ListView):
    template_name = 'common/list.html'
    context_object_name = 'objects'
    paginate_by = 50
    per_page_choices = (50, 100, 200)
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
        raw_per_page = (self.request.GET.get('per_page') or '').strip()
        if raw_per_page.isdigit():
            per_page = int(raw_per_page)
            if per_page in self.per_page_choices:
                return per_page
        return self.paginate_by

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

        params = self.request.GET.copy()
        params.pop('page', None)
        context['query_params'] = params.urlencode()
        return context


class NamedDetailView(DetailView):
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


class NamedCreateView(CreateView):
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


class NamedUpdateView(UpdateView):
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


class NamedDeleteView(DeleteView):
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
