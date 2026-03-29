from django.urls import path

from .views import CompetenceListView

urlpatterns = [
    path('list/', CompetenceListView.as_view(), name='competence_list'),
]