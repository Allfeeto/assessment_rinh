from __future__ import annotations


def prettify_db_error(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return 'Не удалось сохранить данные. Проверьте заполнение формы.'

    first_line = message.splitlines()[0].strip()
    first_lower = first_line.lower()

    if 'assessment_item.program_discipline_id и assessment_item.competence_id' in first_lower:
        return 'Дисциплина учебного плана и компетенция задания должны относиться к одной образовательной программе.'
    if 'отсутствует связь program_discipline -> competence' in first_lower:
        return 'Для выбранной дисциплины учебного плана нет связи с этой компетенцией в матрице дисциплина-компетенция.'
    if 'заведующий кафедрой должен относиться к той же кафедре' in first_lower:
        return 'Заведующий кафедрой должен быть преподавателем этой же кафедры.'
    if 'должны принадлежать одному educational_program' in first_lower:
        return 'Выбраны данные из разных образовательных программ. Проверьте выбранные значения.'
    if 'неизвестный тип задания' in first_lower:
        return (
            'Не удалось сопоставить тип задания для сохранения. '
            'Проверьте тип задания и повторите попытку.'
        )

    return first_line
