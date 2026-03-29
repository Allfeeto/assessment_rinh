-- =========================
-- 1. Справочники
-- =========================

CREATE TABLE education_level (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE department (
    id SERIAL PRIMARY KEY,
    short_name TEXT NOT NULL,
    full_name TEXT NOT NULL
);

CREATE TABLE competence_type (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE assessment_item_type (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- =========================
-- 2. Основные сущности
-- =========================

CREATE TABLE educational_program (
    id SERIAL PRIMARY KEY,
    education_level_id INTEGER NOT NULL REFERENCES education_level(id) ON DELETE RESTRICT,
    department_id INTEGER NOT NULL REFERENCES department(id) ON DELETE RESTRICT,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (code)
);

CREATE TABLE discipline (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

-- Дисциплина в рамках конкретной программы
CREATE TABLE program_discipline (
    id SERIAL PRIMARY KEY,
    educational_program_id INTEGER NOT NULL REFERENCES educational_program(id) ON DELETE CASCADE,
    discipline_id INTEGER NOT NULL REFERENCES discipline(id) ON DELETE RESTRICT,
    UNIQUE (educational_program_id, discipline_id)
);

-- Компетенции
CREATE TABLE competence (
    id SERIAL PRIMARY KEY,
    educational_program_id INTEGER NOT NULL REFERENCES educational_program(id) ON DELETE CASCADE,
    competence_type_id INTEGER NOT NULL REFERENCES competence_type(id) ON DELETE RESTRICT,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (educational_program_id, code)
);

-- Матрица: дисциплина -> компетенции
CREATE TABLE discipline_competence (
    id SERIAL PRIMARY KEY,
    program_discipline_id INTEGER NOT NULL REFERENCES program_discipline(id) ON DELETE CASCADE,
    competence_id INTEGER NOT NULL REFERENCES competence(id) ON DELETE CASCADE,
    UNIQUE (program_discipline_id, competence_id)
);

-- =========================
-- 3. Оценочные средства
-- =========================

CREATE TABLE assessment_item (
    id SERIAL PRIMARY KEY,
    program_discipline_id INTEGER NOT NULL REFERENCES program_discipline(id) ON DELETE CASCADE,
    assessment_item_type_id INTEGER NOT NULL REFERENCES assessment_item_type(id) ON DELETE RESTRICT,
    text TEXT NOT NULL
);

-- Связь задания с компетенциями
CREATE TABLE assessment_item_competence (
    assessment_item_id INTEGER NOT NULL REFERENCES assessment_item(id) ON DELETE CASCADE,
    competence_id INTEGER NOT NULL REFERENCES competence(id) ON DELETE CASCADE,
    PRIMARY KEY (assessment_item_id, competence_id)
);

-- =========================
-- 4. Ответы: выбор (один / несколько)
-- =========================

CREATE TABLE assessment_option (
    id SERIAL PRIMARY KEY,
    assessment_item_id INTEGER NOT NULL REFERENCES assessment_item(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    sort_order INTEGER NOT NULL
);

-- =========================
-- 5. Соответствие
-- =========================

CREATE TABLE assessment_match_left_item (
    id SERIAL PRIMARY KEY,
    assessment_item_id INTEGER NOT NULL REFERENCES assessment_item(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    text TEXT NOT NULL,
    sort_order INTEGER NOT NULL
);

CREATE TABLE assessment_match_right_item (
    id SERIAL PRIMARY KEY,
    assessment_item_id INTEGER NOT NULL REFERENCES assessment_item(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    text TEXT NOT NULL,
    sort_order INTEGER NOT NULL
);

CREATE TABLE assessment_match_answer (
    left_item_id INTEGER NOT NULL REFERENCES assessment_match_left_item(id) ON DELETE CASCADE,
    right_item_id INTEGER NOT NULL REFERENCES assessment_match_right_item(id) ON DELETE CASCADE,
    PRIMARY KEY (left_item_id, right_item_id)
);

-- =========================
-- 6. Последовательность
-- =========================

CREATE TABLE assessment_sequence_item (
    id SERIAL PRIMARY KEY,
    assessment_item_id INTEGER NOT NULL REFERENCES assessment_item(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    correct_order INTEGER NOT NULL
);

-- =========================
-- 7. Открытые ответы
-- =========================

CREATE TABLE assessment_open_answer (
    id SERIAL PRIMARY KEY,
    assessment_item_id INTEGER NOT NULL REFERENCES assessment_item(id) ON DELETE CASCADE,
    text TEXT NOT NULL
);