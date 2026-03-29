from django.urls import path

from .views import CompetenceListView, CompetencePageListView

urlpatterns = [
    path('', CompetencePageListView.as_view(), name='competence_page_list'),
    path('list/', CompetenceListView.as_view(), name='competence_list'),
]
