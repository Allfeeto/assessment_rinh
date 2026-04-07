from django.urls import path

from .views import (
    AssessmentItemCreateView,
    AssessmentItemDeleteView,
    AssessmentItemDetailView,
    AssessmentItemListView,
    AssessmentItemUpdateView,
)

urlpatterns = [
    path('', AssessmentItemListView.as_view(), name='assessment_list'),
    path('create/', AssessmentItemCreateView.as_view(), name='assessment_create'),
    path('<int:pk>/', AssessmentItemDetailView.as_view(), name='assessment_detail'),
    path('<int:pk>/edit/', AssessmentItemUpdateView.as_view(), name='assessment_update'),
    path('<int:pk>/delete/', AssessmentItemDeleteView.as_view(), name='assessment_delete'),
]