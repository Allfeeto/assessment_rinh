import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection

from assessment.forms import AssessmentItemForm
from assessment.models import AssessmentItem, AssessmentItemCompetence
from assessment.selectors import (
    count_items_by_competence,
    count_items_by_program_discipline_competence,
    filter_items_by_competence,
)
from competencies.models import Competence, DisciplineCompetence
from core.models import (
    AcademicDegree,
    AcademicTitle,
    AssessmentItemType,
    CompetenceType,
    EducationLevel,
)
from disciplines.models import Discipline, ProgramDiscipline
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection
from teachers.models import Department, Teacher, TeacherProgramDiscipline
from core.permissions import SENIOR_TEACHER_GROUP_NAME


@pytest.fixture()
def selector_schema():
    if connection.vendor != 'sqlite':
        pytest.skip('Selector unit tests create unmanaged tables only in sqlite.')

    models = [
        ContentType,
        Permission,
        Group,
        User,
        EducationLevel,
        CompetenceType,
        AssessmentItemType,
        AcademicDegree,
        AcademicTitle,
        Department,
        Teacher,
        TrainingDirection,
        ProgramProfile,
        EducationalProgram,
        Discipline,
        ProgramDiscipline,
        Competence,
        DisciplineCompetence,
        TeacherProgramDiscipline,
        AssessmentItem,
        AssessmentItemCompetence,
    ]

    with connection.schema_editor() as schema_editor:
        for model in models:
            schema_editor.create_model(model)

    yield

    with connection.schema_editor() as schema_editor:
        for model in reversed(models):
            schema_editor.delete_model(model)


def _base_refs():
    level = EducationLevel.objects.create(name='Selector level')
    direction = TrainingDirection.objects.create(
        education_level=level,
        code='98.03.01',
        name='Selector direction',
    )
    profile = ProgramProfile.objects.create(
        training_direction=direction,
        code='98.03.01.01',
        name='Selector profile',
    )
    department = Department.objects.create(
        number='998',
        short_name='SEL',
        full_name='Selector department',
    )
    program = EducationalProgram.objects.create(
        program_profile=profile,
        department=department,
        admission_year=2098,
    )
    discipline = Discipline.objects.create(name='Selector discipline')
    program_discipline = ProgramDiscipline.objects.create(
        educational_program=program,
        discipline=discipline,
    )
    competence_type = CompetenceType.objects.create(name='SEL')
    comp_a = Competence.objects.create(
        educational_program=program,
        competence_type=competence_type,
        code='SEL-1',
        name='Selector competence A',
    )
    comp_b = Competence.objects.create(
        educational_program=program,
        competence_type=competence_type,
        code='SEL-2',
        name='Selector competence B',
    )
    DisciplineCompetence.objects.create(program_discipline=program_discipline, competence=comp_a)
    DisciplineCompetence.objects.create(program_discipline=program_discipline, competence=comp_b)
    item_type = AssessmentItemType.objects.create(code='single', name='Single choice')
    return program_discipline, item_type, comp_a, comp_b


def test_competence_selectors_include_legacy_fk_and_m2m(selector_schema):
    program_discipline, item_type, comp_a, comp_b = _base_refs()
    legacy_item = AssessmentItem.objects.create(
        program_discipline=program_discipline,
        competence=comp_a,
        assessment_item_type=item_type,
        prompt_text='Legacy FK only',
    )
    m2m_item = AssessmentItem.objects.create(
        program_discipline=program_discipline,
        competence=None,
        assessment_item_type=item_type,
        prompt_text='M2M only',
    )
    AssessmentItemCompetence.objects.create(assessment_item=m2m_item, competence=comp_b)
    duplicated_item = AssessmentItem.objects.create(
        program_discipline=program_discipline,
        competence=comp_a,
        assessment_item_type=item_type,
        prompt_text='Same competence in both sources',
    )
    AssessmentItemCompetence.objects.create(assessment_item=duplicated_item, competence=comp_a)
    split_item = AssessmentItem.objects.create(
        program_discipline=program_discipline,
        competence=comp_a,
        assessment_item_type=item_type,
        prompt_text='Different FK and M2M competences',
    )
    AssessmentItemCompetence.objects.create(assessment_item=split_item, competence=comp_b)

    item_ids = AssessmentItem.objects.values('pk')

    assert count_items_by_competence(item_ids, [comp_a.id, comp_b.id]) == {
        comp_a.id: 3,
        comp_b.id: 2,
    }
    assert count_items_by_program_discipline_competence(
        item_ids,
        [
            (program_discipline.id, comp_a.id),
            (program_discipline.id, comp_b.id),
        ],
    ) == {
        (program_discipline.id, comp_a.id): 3,
        (program_discipline.id, comp_b.id): 2,
    }
    assert set(
        filter_items_by_competence(AssessmentItem.objects.all(), comp_b.id).values_list('id', flat=True)
    ) == {m2m_item.id, split_item.id}


def test_assessment_item_form_scopes_program_disciplines_for_regular_teacher(selector_schema):
    program_discipline, item_type, comp_a, _comp_b = _base_refs()
    other_discipline = Discipline.objects.create(name='Selector other discipline')
    other_program_discipline = ProgramDiscipline.objects.create(
        educational_program=program_discipline.educational_program,
        discipline=other_discipline,
    )
    user = User.objects.create_user(username='regular-teacher')
    teacher = Teacher.objects.create(
        user=user,
        department=Department.objects.first(),
        full_name='Regular Teacher',
    )
    TeacherProgramDiscipline.objects.create(
        teacher=teacher,
        program_discipline=program_discipline,
    )

    assigned_form = AssessmentItemForm(
        user=user,
        initial={
            'program_discipline': program_discipline.id,
            'assessment_item_type': item_type.id,
            'competencies': [comp_a.id],
        },
    )
    forbidden_form = AssessmentItemForm(
        user=user,
        initial={'program_discipline': other_program_discipline.id},
    )

    assert list(assigned_form.fields['program_discipline'].queryset) == [program_discipline]
    assert list(forbidden_form.fields['program_discipline'].queryset) == []


def test_assessment_item_form_gives_senior_teacher_global_program_discipline_scope(selector_schema):
    program_discipline, _item_type, _comp_a, _comp_b = _base_refs()
    other_discipline = Discipline.objects.create(name='Selector senior discipline')
    other_program_discipline = ProgramDiscipline.objects.create(
        educational_program=program_discipline.educational_program,
        discipline=other_discipline,
    )
    senior_group = Group.objects.create(name=SENIOR_TEACHER_GROUP_NAME)
    user = User.objects.create_user(username='senior-teacher')
    user.groups.add(senior_group)

    form = AssessmentItemForm(
        user=user,
        initial={'program_discipline': other_program_discipline.id},
    )

    assert list(form.fields['program_discipline'].queryset) == [other_program_discipline]
