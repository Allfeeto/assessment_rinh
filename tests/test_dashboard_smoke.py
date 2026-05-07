from assessment.models import AssessmentItem
from competencies import views


def test_competencies_dashboard_keeps_assessment_item_dependency():
    assert views.AssessmentItem is AssessmentItem
