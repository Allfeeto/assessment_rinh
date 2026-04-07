-- =========================================================
-- БАЗОВАЯ СХЕМА ДЛЯ ДИПЛОМА
-- PostgreSQL
-- Полный create-скрипт
-- =========================================================

-- Если база пустая, можно запускать как есть.
-- Если таблицы уже существуют, сначала удаляй их отдельно
-- или выполняй в новой БД.

BEGIN;

-- =========================================================
-- 1. Справочники
-- =========================================================

CREATE TABLE education_level (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE competence_type (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE assessment_item_type (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
    -- например:
    -- 'single_choice'
    -- 'multiple_choice'
    -- 'matching'
    -- 'sequence'
    -- 'open_answer'
);

CREATE TABLE academic_degree (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
    -- например: "кандидат технических наук"
);

CREATE TABLE academic_title (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
    -- например: "доцент", "профессор"
);

-- =========================================================
-- 2. Кафедры и преподаватели
-- =========================================================

CREATE TABLE department (
    id SERIAL PRIMARY KEY,
    number VARCHAR(20) NOT NULL UNIQUE,
    short_name TEXT NOT NULL,
    full_name TEXT NOT NULL
);

CREATE TABLE teacher (
    id SERIAL PRIMARY KEY,
    department_id INTEGER NOT NULL
        REFERENCES department(id)
        ON DELETE RESTRICT,
    full_name TEXT NOT NULL,
    academic_degree_id INTEGER
        REFERENCES academic_degree(id)
        ON DELETE RESTRICT,
    academic_title_id INTEGER
        REFERENCES academic_title(id)
        ON DELETE RESTRICT
);

ALTER TABLE department
ADD COLUMN head_teacher_id INTEGER
    REFERENCES teacher(id)
    ON DELETE RESTRICT;

-- =========================================================
-- 3. Направления / специальности и профили
-- =========================================================

-- Направление / специальность
CREATE TABLE training_direction (
    id SERIAL PRIMARY KEY,
    education_level_id INTEGER NOT NULL
        REFERENCES education_level(id)
        ON DELETE RESTRICT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name TEXT NOT NULL
    -- пример:
    -- 38.03.06 | Торговое дело
);

-- Профиль внутри направления
CREATE TABLE program_profile (
    id SERIAL PRIMARY KEY,
    training_direction_id INTEGER NOT NULL
        REFERENCES training_direction(id)
        ON DELETE CASCADE,
    code VARCHAR(30) NOT NULL UNIQUE,
    name TEXT NOT NULL,
    UNIQUE (training_direction_id, name)
    -- пример:
    -- 38.03.06.09 | Маркетинговое управление бизнес-процессами
    -- 38.03.06.10 | Цифровой маркетинг
);

-- Конкретный учебный план / образовательная программа
-- Профиль + кафедра + год набора
CREATE TABLE educational_program (
    id SERIAL PRIMARY KEY,
    program_profile_id INTEGER NOT NULL
        REFERENCES program_profile(id)
        ON DELETE RESTRICT,
    department_id INTEGER NOT NULL
        REFERENCES department(id)
        ON DELETE RESTRICT,
    admission_year SMALLINT NOT NULL
        CHECK (admission_year BETWEEN 2000 AND 2100),
    UNIQUE (program_profile_id, department_id, admission_year)
);

-- =========================================================
-- 4. Дисциплины, компетенции, матрица
-- =========================================================

CREATE TABLE discipline (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- Дисциплина в рамках конкретного учебного плана
CREATE TABLE program_discipline (
    id SERIAL PRIMARY KEY,
    educational_program_id INTEGER NOT NULL
        REFERENCES educational_program(id)
        ON DELETE CASCADE,
    discipline_id INTEGER NOT NULL
        REFERENCES discipline(id)
        ON DELETE RESTRICT,
    UNIQUE (educational_program_id, discipline_id)
);

-- Компетенции конкретного учебного плана
CREATE TABLE competence (
    id SERIAL PRIMARY KEY,
    educational_program_id INTEGER NOT NULL
        REFERENCES educational_program(id)
        ON DELETE CASCADE,
    competence_type_id INTEGER NOT NULL
        REFERENCES competence_type(id)
        ON DELETE RESTRICT,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (educational_program_id, code)
);

-- Матрица "дисциплина -> компетенция"
CREATE TABLE discipline_competence (
    id SERIAL PRIMARY KEY,
    program_discipline_id INTEGER NOT NULL
        REFERENCES program_discipline(id)
        ON DELETE CASCADE,
    competence_id INTEGER NOT NULL
        REFERENCES competence(id)
        ON DELETE CASCADE,
    UNIQUE (program_discipline_id, competence_id)
);

-- =========================================================
-- 5. Оценочные средства
-- =========================================================

-- Само задание
CREATE TABLE assessment_item (
    id SERIAL PRIMARY KEY,
    program_discipline_id INTEGER NOT NULL
        REFERENCES program_discipline(id)
        ON DELETE CASCADE,
    assessment_item_type_id INTEGER NOT NULL
        REFERENCES assessment_item_type(id)
        ON DELETE RESTRICT,

    -- Основной текст задания
    prompt_text TEXT NOT NULL,

    -- Дополнительная инструкция по выполнению
    instruction_text TEXT,

    -- Для заданий на соответствие могут понадобиться названия колонок
    left_column_title TEXT,
    right_column_title TEXT
);

-- Связь задания с компетенциями
CREATE TABLE assessment_item_competence (
    assessment_item_id INTEGER NOT NULL
        REFERENCES assessment_item(id)
        ON DELETE CASCADE,
    competence_id INTEGER NOT NULL
        REFERENCES competence(id)
        ON DELETE CASCADE,
    PRIMARY KEY (assessment_item_id, competence_id)
);

-- Универсальная таблица элементов задания
CREATE TABLE assessment_item_row (
    id SERIAL PRIMARY KEY,
    assessment_item_id INTEGER NOT NULL
        REFERENCES assessment_item(id)
        ON DELETE CASCADE,

    -- Тип строки внутри задания:
    -- option                -> вариант ответа для single/multiple choice
    -- match_pair            -> корректная пара для задания на соответствие
    -- match_right_distractor-> лишний элемент правой колонки для соответствия
    -- sequence              -> элемент последовательности
    -- open_answer           -> допустимый вариант открытого ответа
    row_kind VARCHAR(30) NOT NULL
        CHECK (
            row_kind IN (
                'option',
                'match_pair',
                'match_right_distractor',
                'sequence',
                'open_answer'
            )
        ),

    -- Маркеры для вывода в шаблон (А, Б, В / 1, 2, 3 и т.п.)
    left_label TEXT,
    right_label TEXT,

    -- Универсальные поля
    left_text TEXT,
    right_text TEXT,

    -- Порядок отображения строки в интерфейсе / печати
    sort_order INTEGER CHECK (sort_order IS NULL OR sort_order > 0),

    -- Правильный порядок для sequence
    correct_order INTEGER CHECK (correct_order IS NULL OR correct_order > 0),

    -- Признак правильности для single/multiple choice
    is_correct BOOLEAN,

    -- Допустимый ответ для open_answer
    open_answer_text TEXT,

    -- Хотя бы одно смысловое поле должно быть заполнено
    CHECK (
        NULLIF(BTRIM(COALESCE(left_text, '')), '') IS NOT NULL
        OR NULLIF(BTRIM(COALESCE(right_text, '')), '') IS NOT NULL
        OR NULLIF(BTRIM(COALESCE(open_answer_text, '')), '') IS NOT NULL
    )
);

-- Чтобы не было дублей по порядку внутри одного задания и одного типа строки
CREATE UNIQUE INDEX uq_assessment_item_row_kind_sort
    ON assessment_item_row (assessment_item_id, row_kind, sort_order)
    WHERE sort_order IS NOT NULL;

-- =========================================================
-- 6. Индексы по внешним ключам
-- =========================================================

CREATE INDEX idx_teacher_department_id
    ON teacher(department_id);

CREATE INDEX idx_department_head_teacher_id
    ON department(head_teacher_id);

CREATE INDEX idx_training_direction_education_level_id
    ON training_direction(education_level_id);

CREATE INDEX idx_program_profile_training_direction_id
    ON program_profile(training_direction_id);

CREATE INDEX idx_educational_program_program_profile_id
    ON educational_program(program_profile_id);

CREATE INDEX idx_educational_program_department_id
    ON educational_program(department_id);

CREATE INDEX idx_program_discipline_educational_program_id
    ON program_discipline(educational_program_id);

CREATE INDEX idx_program_discipline_discipline_id
    ON program_discipline(discipline_id);

CREATE INDEX idx_competence_educational_program_id
    ON competence(educational_program_id);

CREATE INDEX idx_competence_competence_type_id
    ON competence(competence_type_id);

CREATE INDEX idx_discipline_competence_program_discipline_id
    ON discipline_competence(program_discipline_id);

CREATE INDEX idx_discipline_competence_competence_id
    ON discipline_competence(competence_id);

CREATE INDEX idx_assessment_item_program_discipline_id
    ON assessment_item(program_discipline_id);

CREATE INDEX idx_assessment_item_assessment_item_type_id
    ON assessment_item(assessment_item_type_id);

CREATE INDEX idx_assessment_item_competence_competence_id
    ON assessment_item_competence(competence_id);

CREATE INDEX idx_assessment_item_row_assessment_item_id
    ON assessment_item_row(assessment_item_id);

CREATE INDEX idx_assessment_item_row_row_kind
    ON assessment_item_row(row_kind);

-- =========================================================
-- 7. Триггеры целостности
-- =========================================================

-- 7.1. Проверка: код профиля должен начинаться с кода направления
CREATE OR REPLACE FUNCTION check_program_profile_code_prefix()
RETURNS TRIGGER AS $$
DECLARE
    v_direction_code TEXT;
BEGIN
    SELECT code
    INTO v_direction_code
    FROM training_direction
    WHERE id = NEW.training_direction_id;

    IF v_direction_code IS NULL THEN
        RAISE EXCEPTION 'Не найдено направление для profile.training_direction_id=%',
            NEW.training_direction_id;
    END IF;

    IF NEW.code NOT LIKE v_direction_code || '.%' THEN
        RAISE EXCEPTION
            'Код профиля "%" должен начинаться с кода направления "%."',
            NEW.code, v_direction_code;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_program_profile_code_prefix
BEFORE INSERT OR UPDATE ON program_profile
FOR EACH ROW
EXECUTE FUNCTION check_program_profile_code_prefix();


-- 7.2. Проверка: заведующий кафедрой должен принадлежать этой же кафедре
CREATE OR REPLACE FUNCTION check_department_head_teacher()
RETURNS TRIGGER AS $$
DECLARE
    v_teacher_department_id INTEGER;
BEGIN
    IF NEW.head_teacher_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT department_id
    INTO v_teacher_department_id
    FROM teacher
    WHERE id = NEW.head_teacher_id;

    IF v_teacher_department_id IS NULL THEN
        RAISE EXCEPTION 'Преподаватель с id=% не найден', NEW.head_teacher_id;
    END IF;

    IF v_teacher_department_id <> NEW.id THEN
        RAISE EXCEPTION
            'Заведующий кафедрой должен относиться к той же кафедре. department.id=%, teacher.department_id=%',
            NEW.id, v_teacher_department_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_department_head_teacher
BEFORE INSERT OR UPDATE ON department
FOR EACH ROW
EXECUTE FUNCTION check_department_head_teacher();


-- 7.3. Проверка: дисциплина и компетенция в discipline_competence
-- должны относиться к одному и тому же учебному плану
CREATE OR REPLACE FUNCTION check_discipline_competence_same_program()
RETURNS TRIGGER AS $$
DECLARE
    v_pd_program_id INTEGER;
    v_comp_program_id INTEGER;
BEGIN
    SELECT educational_program_id
    INTO v_pd_program_id
    FROM program_discipline
    WHERE id = NEW.program_discipline_id;

    SELECT educational_program_id
    INTO v_comp_program_id
    FROM competence
    WHERE id = NEW.competence_id;

    IF v_pd_program_id IS NULL OR v_comp_program_id IS NULL THEN
        RAISE EXCEPTION 'Не найдена дисциплина плана или компетенция';
    END IF;

    IF v_pd_program_id <> v_comp_program_id THEN
        RAISE EXCEPTION
            'program_discipline и competence должны принадлежать одному educational_program';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_discipline_competence_same_program
BEFORE INSERT OR UPDATE ON discipline_competence
FOR EACH ROW
EXECUTE FUNCTION check_discipline_competence_same_program();


-- 7.4. Проверка: задание и компетенция в assessment_item_competence
-- должны относиться к одному и тому же учебному плану
CREATE OR REPLACE FUNCTION check_assessment_item_competence_same_program()
RETURNS TRIGGER AS $$
DECLARE
    v_item_program_id INTEGER;
    v_comp_program_id INTEGER;
BEGIN
    SELECT pd.educational_program_id
    INTO v_item_program_id
    FROM assessment_item ai
    JOIN program_discipline pd ON pd.id = ai.program_discipline_id
    WHERE ai.id = NEW.assessment_item_id;

    SELECT educational_program_id
    INTO v_comp_program_id
    FROM competence
    WHERE id = NEW.competence_id;

    IF v_item_program_id IS NULL OR v_comp_program_id IS NULL THEN
        RAISE EXCEPTION 'Не найдено задание или компетенция';
    END IF;

    IF v_item_program_id <> v_comp_program_id THEN
        RAISE EXCEPTION
            'assessment_item и competence должны принадлежать одному educational_program';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_assessment_item_competence_same_program
BEFORE INSERT OR UPDATE ON assessment_item_competence
FOR EACH ROW
EXECUTE FUNCTION check_assessment_item_competence_same_program();

COMMIT;