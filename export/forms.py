from django import forms


class WordExportForm(forms.Form):
    program_id = forms.IntegerField(required=True)
    discipline_id = forms.IntegerField(required=True)
    assessment_item_type = forms.IntegerField(required=False)
    competence = forms.IntegerField(required=False)