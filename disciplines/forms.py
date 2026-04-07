from django import forms

from .models import Discipline, ProgramDiscipline


class DisciplineForm(forms.ModelForm):
    class Meta:
        model = Discipline
        fields = ('name',)


class ProgramDisciplineForm(forms.ModelForm):
    class Meta:
        model = ProgramDiscipline
        fields = ('educational_program', 'discipline')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['educational_program'].queryset = self.fields['educational_program'].queryset.select_related(
            'program_profile',
            'department',
        ).order_by(
            'program_profile__code',
            'admission_year',
        )
        self.fields['discipline'].queryset = self.fields['discipline'].queryset.order_by('name')
