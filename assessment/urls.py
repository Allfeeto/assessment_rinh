from django.urls import path

from .views import (
    AssessmentItemCreateView,
    AssessmentItemDeleteView,
    AssessmentItemDetailView,
    AssessmentItemListView,
    AssessmentItemUpdateView,
    TeacherWorkspaceClearClipboardView,
    TeacherWorkspaceCopyItemsView,
    TeacherWorkspacePasteItemsView,
    TeacherWorkspaceView,
)

urlpatterns = [
    path('', AssessmentItemListView.as_view(), name='assessment_list'),
    path('workspace/', TeacherWorkspaceView.as_view(), name='assessment_workspace'),
    path('workspace/copy/', TeacherWorkspaceCopyItemsView.as_view(), name='assessment_workspace_copy'),
    path('workspace/paste/', TeacherWorkspacePasteItemsView.as_view(), name='assessment_workspace_paste'),
    path('workspace/clipboard/clear/', TeacherWorkspaceClearClipboardView.as_view(), name='assessment_workspace_clipboard_clear'),
    path('create/', AssessmentItemCreateView.as_view(), name='assessment_create'),
    path('<int:pk>/', AssessmentItemDetailView.as_view(), name='assessment_detail'),
    path('<int:pk>/edit/', AssessmentItemUpdateView.as_view(), name='assessment_update'),
    path('<int:pk>/delete/', AssessmentItemDeleteView.as_view(), name='assessment_delete'),
]
