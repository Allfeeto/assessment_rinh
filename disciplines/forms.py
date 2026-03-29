from django import forms

from .models import ProgramDiscipline


class ProgramDisciplineForm(forms.ModelForm):
    class Meta:
        model = ProgramDiscipline
        fields = ('educational_program', 'discipline')