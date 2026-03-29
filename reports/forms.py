from django import forms


class ReportFilterForm(forms.Form):
    program = forms.IntegerField(required=False)
    discipline = forms.IntegerField(required=False)
    competence = forms.IntegerField(required=False)