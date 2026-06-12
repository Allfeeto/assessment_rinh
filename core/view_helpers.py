from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .permissions import can_use_model_permission, is_staff_or_superuser


PER_PAGE_CHOICES = (50, 100, 200)
DEFAULT_PER_PAGE = 50
SORT_DIRECTIONS = {'asc', 'desc'}


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


def query_params_with(request, *, values=None, remove=()):
    params = request.GET.copy()
    for key in remove:
        params.pop(key, None)
    for key, value in (values or {}).items():
        if value in (None, ''):
            params.pop(key, None)
        else:
            params[key] = str(value)
    return params.urlencode()


def compact_queryset_block(
    request,
    queryset,
    *,
    prefix,
    preview_size=8,
    page_size=20,
):
    expanded_param = f'{prefix}_expanded'
    page_param = f'{prefix}_page'
    expanded = request.GET.get(expanded_param) == '1'

    if expanded:
        page_obj = paginate_queryset(
            request,
            queryset,
            page_param=page_param,
            per_page=page_size,
        )
        items = page_obj.object_list
        total_count = page_obj.paginator.count
        page_range = [
            value if isinstance(value, int) else None
            for value in page_obj.paginator.get_elided_page_range(
                page_obj.number,
                on_each_side=1,
                on_ends=1,
            )
        ]
    else:
        page_obj = None
        page_range = []
        total_count = queryset.count()
        items = queryset[:preview_size]

    can_expand = total_count > preview_size
    return {
        'prefix': prefix,
        'items': items,
        'page_obj': page_obj,
        'page_range': page_range,
        'page_param': page_param,
        'pagination_query': query_params_without(request, page_param),
        'total_count': total_count,
        'expanded': expanded,
        'can_expand': can_expand,
        'expand_query': query_params_with(
            request,
            values={expanded_param: 1},
            remove=(page_param,),
        ),
        'collapse_query': query_params_with(
            request,
            remove=(expanded_param, page_param),
        ),
    }


def normalize_sort(sort_by, sort_direction, sort_options, *, default_sort='', default_direction='asc'):
    if sort_by not in sort_options:
        sort_by = default_sort if default_sort in sort_options else ''
    if sort_direction not in SORT_DIRECTIONS:
        sort_direction = default_direction if default_direction in SORT_DIRECTIONS else 'asc'
    return sort_by, sort_direction


def ordering_for_sort(sort_by, sort_direction, sort_options, default_ordering=()):
    if not sort_by or sort_by not in sort_options:
        return tuple(default_ordering)

    ordering = []
    for field_name in sort_options[sort_by]:
        normalized_field_name = field_name[1:] if field_name.startswith('-') else field_name
        ordering.append(f'-{normalized_field_name}' if sort_direction == 'desc' else normalized_field_name)
    return tuple(ordering)


def sort_link_queries(
    request,
    sort_keys,
    *,
    current_sort='',
    current_direction='asc',
    sort_param='sort',
    direction_param='dir',
    page_param='page',
):
    links = {}
    for sort_key in sort_keys:
        params = request.GET.copy()
        params.pop(page_param, None)
        params[sort_param] = sort_key
        params[direction_param] = (
            'desc' if sort_key == current_sort and current_direction == 'asc' else 'asc'
        )
        links[sort_key] = params.urlencode()
    return links


def resolve_attr(obj, path):
    value = obj
    for part in path.split('.'):
        value = getattr(value, part, None)
        if value is None:
            return ''
    return value


class StaffOrModelPermissionRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
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
    permission_action = 'view'
    template_name = 'common/list.html'
    context_object_name = 'objects'
    paginate_by = DEFAULT_PER_PAGE
    per_page_choices = PER_PAGE_CHOICES
    title = ''
    search_fields = ()
    list_columns = ()
    order_by = ('id',)
    sortable_columns = {}
    list_column_sort_keys = {}
    sort_param = 'sort'
    sort_direction_param = 'dir'
    default_sort = ''
    default_sort_direction = 'asc'
    create_url_name = ''
    detail_url_name = ''
    update_url_name = ''
    delete_url_name = ''

    def get_queryset(self):
        queryset = super().get_queryset()
        current_sort, current_direction = normalize_sort(
            self.request.GET.get(self.sort_param, ''),
            self.request.GET.get(self.sort_direction_param, 'asc'),
            self.sortable_columns,
            default_sort=self.default_sort,
            default_direction=self.default_sort_direction,
        )
        self.current_sort = current_sort
        self.current_sort_direction = current_direction
        queryset = queryset.order_by(
            *ordering_for_sort(current_sort, current_direction, self.sortable_columns, self.order_by)
        )
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
        current_sort = getattr(self, 'current_sort', '')
        current_direction = getattr(self, 'current_sort_direction', 'asc')
        list_sort_links = sort_link_queries(
            self.request,
            self.sortable_columns.keys(),
            current_sort=current_sort,
            current_direction=current_direction,
            sort_param=self.sort_param,
            direction_param=self.sort_direction_param,
            page_param='page',
        )
        context['display_columns'] = [
            {
                'label': label,
                'path': column_path,
                'sort_key': self.list_column_sort_keys.get(column_path, ''),
                'sort_query': list_sort_links.get(self.list_column_sort_keys.get(column_path, ''), ''),
                'is_sorted': bool(self.list_column_sort_keys.get(column_path, '') == current_sort),
                'sort_direction': current_direction,
            }
            for label, column_path in self.list_columns
        ]
        can_view_detail = bool(self.detail_url_name)
        can_change = self.can_use_action('change')
        can_delete = self.can_use_action('delete')
        context['create_url_name'] = self.create_url_name if self.can_use_action('add') else ''
        context['detail_url_name'] = self.detail_url_name
        context['update_url_name'] = self.update_url_name if can_change else ''
        context['delete_url_name'] = self.delete_url_name if can_delete else ''
        context['per_page_choices'] = self.per_page_choices
        context['selected_per_page'] = self.get_paginate_by(context.get('object_list'))

        rows = []
        for obj in context['object_list']:
            rows.append(
                {
                    'object': obj,
                    'values': [resolve_attr(obj, column_path) for _, column_path in self.list_columns],
                    'can_view_detail': can_view_detail,
                    'can_change': bool(self.update_url_name and can_change and self.can_change_object(obj)),
                    'can_delete': bool(self.delete_url_name and can_delete and self.can_delete_object(obj)),
                }
            )
        context['rows'] = rows
        context['has_row_actions'] = can_view_detail or any(
            row['can_view_detail'] or row['can_change'] or row['can_delete']
            for row in rows
        )

        context['query_params'] = query_params_without(self.request, 'page')
        return context

    def can_change_object(self, obj):
        return True

    def can_delete_object(self, obj):
        return True


class NamedDetailView(StaffOrModelPermissionRequiredMixin, DetailView):
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
