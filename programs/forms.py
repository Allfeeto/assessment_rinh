from django import forms

from .models import EducationalProgram, ProgramProfile, TrainingDirection


class TrainingDirectionForm(forms.ModelForm):
    class Meta:
        model = TrainingDirection
        fields = ('education_level', 'code', 'name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['education_level'].queryset = self.fields['education_level'].queryset.order_by('name')


class ProgramProfileForm(forms.ModelForm):
    class Meta:
        model = ProgramProfile
        fields = ('training_direction', 'code', 'name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['training_direction'].queryset = self.fields['training_direction'].queryset.order_by('code')


class EducationalProgramForm(forms.ModelForm):
    training_direction = forms.ModelChoiceField(
        queryset=TrainingDirection.objects.all(),
        required=False,
        label='Направление (для фильтра профилей)',
    )

    class Meta:
        model = EducationalProgram
        fields = ('training_direction', 'program_profile', 'department', 'admission_year')
        widgets = {
            'training_direction': forms.Select(attrs={'data-dependent-child': 'id_program_profile'}),
            'program_profile': forms.Select(
                attrs={
                    'data-fetch-url': '/programs/profiles-by-direction/?direction_id={value}',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['training_direction'].queryset = TrainingDirection.objects.order_by('code')

        direction_id = None
        if self.is_bound:
            direction_id = self.data.get('training_direction')
        elif self.instance and self.instance.pk:
            direction_id = self.instance.program_profile.training_direction_id
            self.fields['training_direction'].initial = direction_id

        profiles = ProgramProfile.objects.select_related('training_direction').order_by('code')
        if direction_id:
            profiles = profiles.filter(training_direction_id=direction_id)
        self.fields['program_profile'].queryset = profiles

    def clean(self):
        cleaned_data = super().clean()
        direction = cleaned_data.get('training_direction')
        profile = cleaned_data.get('program_profile')
        if direction and profile and profile.training_direction_id != direction.id:
            self.add_error('program_profile', 'Профиль должен принадлежать выбранному направлению.')
        return cleaned_data
