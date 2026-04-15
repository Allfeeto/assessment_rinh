from django import forms

from .models import Competence, DisciplineCompetence


class CompetenceForm(forms.ModelForm):
    class Meta:
        model = Competence
        fields = ('educational_program', 'competence_type', 'code', 'name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['educational_program'].queryset = self.fields['educational_program'].queryset.select_related(
            'program_profile',
            'department',
        ).order_by('program_profile__code', 'admission_year')
        self.fields['competence_type'].queryset = self.fields['competence_type'].queryset.order_by('name')


class DisciplineCompetenceForm(forms.ModelForm):
    class Meta:
        model = DisciplineCompetence
        fields = ('program_discipline', 'competence')
        widgets = {
            'program_discipline': forms.Select(attrs={'data-dependent-child': 'id_competence'}),
            'competence': forms.Select(
                attrs={'data-fetch-url': '/competencies/by-program-discipline/?program_discipline_id={value}'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['program_discipline'].queryset = self.fields['program_discipline'].queryset.select_related(
            'educational_program__program_profile',
            'discipline',
        ).order_by(
            'educational_program__program_profile__code',
            'educational_program__admission_year',
            'discipline__name',
        )
        program_discipline_id = None
        if self.is_bound:
            program_discipline_id = self.data.get('program_discipline')
        elif self.instance and self.instance.pk:
            program_discipline_id = self.instance.program_discipline_id

        competence_qs = Competence.objects.none()
        if program_discipline_id:
            educational_program_id = (
                self.fields['program_discipline'].queryset
                .filter(pk=program_discipline_id)
                .values_list('educational_program_id', flat=True)
                .first()
            )
            if educational_program_id:
                competence_qs = (
                    Competence.objects.select_related('competence_type')
                    .filter(educational_program_id=educational_program_id)
                    .order_by('code')
                )

        self.fields['competence'].queryset = competence_qs

    def clean(self):
        cleaned_data = super().clean()
        program_discipline = cleaned_data.get('program_discipline')
        competence = cleaned_data.get('competence')
        if program_discipline and competence:
            if program_discipline.educational_program_id != competence.educational_program_id:
                self.add_error('competence', 'Компетенция должна быть из того же учебного плана.')
        return cleaned_data
