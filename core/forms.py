from django import forms

from .models import EducationalProgram


class EducationalProgramForm(forms.ModelForm):
    class Meta:
        model = EducationalProgram
        fields = ('education_level', 'department', 'code', 'name')