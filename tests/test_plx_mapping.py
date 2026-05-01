from programs.services.plx_mapping import PlxMapper
from programs.services.plx_parser import ParsedPlxDocument


def test_duplicate_discipline_rows_keep_all_competence_links():
    parsed = ParsedPlxDocument(
        source_filename='09.03.02.01_1.plx',
        document_attrs={'УровеньОбразования': 'бакалавриат'},
        tables={
            'Планы': [
                {
                    'Код': 'plan-1',
                    'КодООП': 'oop-main',
                    'ГодНачалаПодготовки': '2025',
                    'КодПрофКафедры': 'dept-1',
                }
            ],
            'ООП': [
                {
                    'Код': 'oop-main',
                    'Шифр': '09.03.02',
                    'Название': 'Информационные системы и технологии',
                }
            ],
            'ООП_вложенные': [
                {
                    'Код': 'oop-profile',
                    'КодРодительскогоООП': 'oop-main',
                    'Название': '09.03.02.01 Информационные системы и технологии',
                    'Используется': 'true',
                }
            ],
            'Кафедры': [
                {
                    'Код': 'dept-1',
                    'Номер': '1',
                    'Сокращение': 'КИТ',
                    'Название': 'Кафедра информационных технологий',
                }
            ],
            'ПланыСтроки': [
                {
                    'КодПлана': 'plan-1',
                    'Код': 'discipline-row-1',
                    'СчитатьВПлане': 'true',
                    'ТипОбъекта': '1',
                    'ДисциплинаКод': 'Б2.В.01',
                    'Дисциплина': 'Производственная практика',
                },
                {
                    'КодПлана': 'plan-1',
                    'Код': 'discipline-row-2',
                    'СчитатьВПлане': 'true',
                    'ТипОбъекта': '1',
                    'ДисциплинаКод': 'Б2.В.02',
                    'Дисциплина': '  Производственная   практика ',
                },
            ],
            'ПланыКомпетенции': [
                {
                    'КодПлана': 'plan-1',
                    'КодООП': 'oop-main',
                    'Код': 'competence-1',
                    'ШифрКомпетенции': 'ПК-1',
                    'Наименование': 'Способен решать одну задачу',
                    'Тип': '4',
                },
                {
                    'КодПлана': 'plan-1',
                    'КодООП': 'oop-main',
                    'Код': 'competence-2',
                    'ШифрКомпетенции': 'ПК-2',
                    'Наименование': 'Способен решать другую задачу',
                    'Тип': '4',
                },
            ],
            'ПланыКомпетенцииДисциплины': [
                {
                    'КодСтроки': 'discipline-row-1',
                    'КодКомпетенции': 'competence-1',
                },
                {
                    'КодСтроки': 'discipline-row-2',
                    'КодКомпетенции': 'competence-2',
                },
            ],
        },
    )

    dto = PlxMapper().map_to_dto(parsed)

    assert [(item.external_id, item.name) for item in dto.disciplines] == [
        ('discipline-row-1', 'Производственная практика'),
        ('discipline-row-2', 'Производственная практика'),
    ]
    assert sorted(
        (link.discipline_external_id, link.competence_external_id)
        for link in dto.discipline_competence_links
    ) == [
        ('discipline-row-1', 'competence-1'),
        ('discipline-row-2', 'competence-2'),
    ]


def test_duplicate_competence_rows_keep_all_discipline_links():
    parsed = ParsedPlxDocument(
        source_filename='09.03.02.01_1.plx',
        document_attrs={'УровеньОбразования': 'бакалавриат'},
        tables={
            'Планы': [
                {
                    'Код': 'plan-1',
                    'КодООП': 'oop-main',
                    'ГодНачалаПодготовки': '2025',
                    'КодПрофКафедры': 'dept-1',
                }
            ],
            'ООП': [
                {
                    'Код': 'oop-main',
                    'Шифр': '09.03.02',
                    'Название': 'Информационные системы и технологии',
                }
            ],
            'ООП_вложенные': [
                {
                    'Код': 'oop-profile',
                    'КодРодительскогоООП': 'oop-main',
                    'Название': '09.03.02.01 Информационные системы и технологии',
                    'Используется': 'true',
                }
            ],
            'Кафедры': [
                {
                    'Код': 'dept-1',
                    'Номер': '1',
                    'Сокращение': 'КИТ',
                    'Название': 'Кафедра информационных технологий',
                }
            ],
            'ПланыСтроки': [
                {
                    'КодПлана': 'plan-1',
                    'Код': 'discipline-row-1',
                    'СчитатьВПлане': 'true',
                    'ТипОбъекта': '1',
                    'Дисциплина': 'Первая дисциплина',
                },
                {
                    'КодПлана': 'plan-1',
                    'Код': 'discipline-row-2',
                    'СчитатьВПлане': 'true',
                    'ТипОбъекта': '1',
                    'Дисциплина': 'Вторая дисциплина',
                },
            ],
            'ПланыКомпетенции': [
                {
                    'КодПлана': 'plan-1',
                    'КодООП': 'oop-main',
                    'Код': 'competence-1',
                    'ШифрКомпетенции': 'ПК-1',
                    'Наименование': 'Способен решать задачу',
                    'Тип': '4',
                },
                {
                    'КодПлана': 'plan-1',
                    'КодООП': 'oop-profile',
                    'Код': 'competence-duplicate',
                    'ШифрКомпетенции': 'ПК-1',
                    'Наименование': 'Способен решать задачу',
                    'Тип': '4',
                },
            ],
            'ПланыКомпетенцииДисциплины': [
                {
                    'КодСтроки': 'discipline-row-1',
                    'КодКомпетенции': 'competence-1',
                },
                {
                    'КодСтроки': 'discipline-row-2',
                    'КодКомпетенции': 'competence-duplicate',
                },
            ],
        },
    )

    dto = PlxMapper().map_to_dto(parsed)

    assert [(item.external_id, item.code) for item in dto.competences] == [
        ('competence-1', 'ПК-1')
    ]
    assert [
        (link.discipline_external_id, link.competence_external_id)
        for link in dto.discipline_competence_links
    ] == [
        ('discipline-row-1', 'competence-1'),
        ('discipline-row-2', 'competence-1'),
    ]
