from django.urls import path

from .views import (
    AssessmentItemCreateView,
    AssessmentItemDeleteView,
    AssessmentItemDetailView,
    AssessmentItemListView,
    AssessmentItemUpdateView,
)

urlpatterns = [
    path('items/', AssessmentItemListView.as_view(), name='assessment_item_list'),
    path('items/create/', AssessmentItemCreateView.as_view(), name='assessment_item_create'),
    path('items/<int:pk>/', AssessmentItemDetailView.as_view(), name='assessment_item_detail'),
    path('items/<int:pk>/edit/', AssessmentItemUpdateView.as_view(), name='assessment_item_update'),
    path('items/<int:pk>/delete/', AssessmentItemDeleteView.as_view(), name='assessment_item_delete'),
]