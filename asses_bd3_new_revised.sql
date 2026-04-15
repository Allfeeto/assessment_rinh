-- =========================================================
-- БАЗОВАЯ СХЕМА ДЛЯ ДИПЛОМА
-- PostgreSQL
-- Полный create-скрипт
-- РЕДАКЦИЯ: упрощена модель assessment_item / assessment_item_row
-- =========================================================

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
    -- 'выбор одного ответа'
    -- 'выбор нескольких ответов'
    -- 'установление соответствия'
    -- 'установление последовательности'
    -- 'открытый ответ'
);

CREATE TABLE academic_degree (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE academic_title (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
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

CREATE TABLE training_direction (
    id SERIAL PRIMARY KEY,
    education_level_id INTEGER NOT NULL
        REFERENCES education_level(id)
        ON DELETE RESTRICT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE program_profile (
    id SERIAL PRIMARY KEY,
    training_direction_id INTEGER NOT NULL
        REFERENCES training_direction(id)
        ON DELETE CASCADE,
    code VARCHAR(30) NOT NULL UNIQUE,
    name TEXT NOT NULL,
    UNIQUE (training_direction_id, name)
);

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

CREATE TABLE assessment_item (
    id SERIAL PRIMARY KEY,
    program_discipline_id INTEGER NOT NULL
        REFERENCES program_discipline(id)
        ON DELETE CASCADE,
    competence_id INTEGER NOT NULL
        REFERENCES competence(id)
        ON DELETE RESTRICT,
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

-- Таблица строк задания без row_kind и без label-полей.
-- Тип строки определяется типом задания.
-- Для соответствия:
--   заполнены left_text + right_text -> корректная пара
--   заполнен только right_text       -> правый дистрактор
CREATE TABLE assessment_item_row (
    id SERIAL PRIMARY KEY,
    assessment_item_id INTEGER NOT NULL
        REFERENCES assessment_item(id)
        ON DELETE CASCADE,

    left_text TEXT,
    right_text TEXT,

    -- Порядок отображения строки в интерфейсе.
    -- Для печати и ключей может не использоваться напрямую,
    -- если приложение применяет отдельную рандомизацию.
    sort_order INTEGER CHECK (sort_order IS NULL OR sort_order > 0),

    -- Правильный порядок для задания на последовательность
    correct_order INTEGER CHECK (correct_order IS NULL OR correct_order > 0),

    -- Признак правильности для single/multiple choice
    is_correct BOOLEAN,

    -- Допустимый ответ для open_answer
    open_answer_text TEXT,

    CHECK (
        NULLIF(BTRIM(COALESCE(left_text, '')), '') IS NOT NULL
        OR NULLIF(BTRIM(COALESCE(right_text, '')), '') IS NOT NULL
        OR NULLIF(BTRIM(COALESCE(open_answer_text, '')), '') IS NOT NULL
    )
);

CREATE UNIQUE INDEX uq_assessment_item_row_sort
    ON assessment_item_row (assessment_item_id, sort_order)
    WHERE sort_order IS NOT NULL;

CREATE UNIQUE INDEX uq_assessment_item_row_correct_order
    ON assessment_item_row (assessment_item_id, correct_order)
    WHERE correct_order IS NOT NULL;

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

CREATE INDEX idx_assessment_item_competence_id
    ON assessment_item(competence_id);

CREATE INDEX idx_assessment_item_assessment_item_type_id
    ON assessment_item(assessment_item_type_id);

CREATE INDEX idx_assessment_item_row_assessment_item_id
    ON assessment_item_row(assessment_item_id);

-- =========================================================
-- 7. Триггеры целостности
-- =========================================================

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


-- Проверка: задание должно ссылаться на компетенцию той же программы,
-- и эта пара discipline -> competence должна существовать в discipline_competence.
CREATE OR REPLACE FUNCTION check_assessment_item_relation_integrity()
RETURNS TRIGGER AS $$
DECLARE
    v_pd_program_id INTEGER;
    v_comp_program_id INTEGER;
    v_exists_pair INTEGER;
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
        RAISE EXCEPTION 'Не найдена дисциплина плана или компетенция для задания';
    END IF;

    IF v_pd_program_id <> v_comp_program_id THEN
        RAISE EXCEPTION
            'assessment_item.program_discipline_id и assessment_item.competence_id должны принадлежать одному educational_program';
    END IF;

    SELECT 1
    INTO v_exists_pair
    FROM discipline_competence dc
    WHERE dc.program_discipline_id = NEW.program_discipline_id
      AND dc.competence_id = NEW.competence_id;

    IF v_exists_pair IS NULL THEN
        RAISE EXCEPTION
            'Для задания отсутствует связь program_discipline -> competence в таблице discipline_competence';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_assessment_item_relation_integrity
BEFORE INSERT OR UPDATE ON assessment_item
FOR EACH ROW
EXECUTE FUNCTION check_assessment_item_relation_integrity();


-- Проверка строк задания с учетом типа задания.
-- Логика опирается на стандартные значения справочника assessment_item_type.name.
CREATE OR REPLACE FUNCTION public.check_assessment_item_row_by_type()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
DECLARE
    v_item_type_name TEXT;
    v_left_text  TEXT := NULLIF(BTRIM(COALESCE(NEW.left_text, '')), '');
    v_right_text TEXT := NULLIF(BTRIM(COALESCE(NEW.right_text, '')), '');
    v_answer_text TEXT := NULLIF(BTRIM(COALESCE(NEW.open_answer_text, '')), '');
BEGIN
    SELECT ait.name
    INTO v_item_type_name
    FROM assessment_item ai
    JOIN assessment_item_type ait ON ait.id = ai.assessment_item_type_id
    WHERE ai.id = NEW.assessment_item_id;

    IF v_item_type_name IS NULL THEN
        RAISE EXCEPTION 'Не найден тип задания для assessment_item_id=%', NEW.assessment_item_id;
    END IF;

    IF v_item_type_name IN ('Задание закрытого типа с выбором одного верного ответа из предложенных', 'Задание закрытого типа с выбором нескольких верных ответов из предложенных') THEN
        IF v_left_text IS NULL THEN
            RAISE EXCEPTION 'Для заданий с выбором ответа left_text обязателен';
        END IF;
        IF v_right_text IS NOT NULL OR v_answer_text IS NOT NULL THEN
            RAISE EXCEPTION 'Для заданий с выбором ответа допускаются только left_text, is_correct, sort_order';
        END IF;
        IF NEW.is_correct IS NULL THEN
            RAISE EXCEPTION 'Для заданий с выбором ответа is_correct обязателен';
        END IF;
        IF NEW.correct_order IS NOT NULL THEN
            RAISE EXCEPTION 'Для заданий с выбором ответа correct_order должен быть NULL';
        END IF;

    ELSIF v_item_type_name = 'Задание закрытого типа на установление соответствия' THEN
        IF v_right_text IS NULL THEN
            RAISE EXCEPTION 'Для задания на соответствие right_text обязателен';
        END IF;
        IF v_answer_text IS NOT NULL THEN
            RAISE EXCEPTION 'Для задания на соответствие open_answer_text должен быть NULL';
        END IF;
        IF NEW.is_correct IS NOT NULL THEN
            RAISE EXCEPTION 'Для задания на соответствие is_correct не используется';
        END IF;
        IF NEW.correct_order IS NOT NULL THEN
            RAISE EXCEPTION 'Для задания на соответствие correct_order не используется';
        END IF;
        -- left_text может быть NULL: это правый дистрактор.

    ELSIF v_item_type_name = 'Задание закрытого типа на установление последовательности' THEN
        IF v_left_text IS NULL THEN
            RAISE EXCEPTION 'Для задания на последовательность left_text обязателен';
        END IF;
        IF NEW.correct_order IS NULL THEN
            RAISE EXCEPTION 'Для задания на последовательность correct_order обязателен';
        END IF;
        IF v_right_text IS NOT NULL OR v_answer_text IS NOT NULL OR NEW.is_correct IS NOT NULL THEN
            RAISE EXCEPTION 'Для задания на последовательность допускаются только left_text, sort_order, correct_order';
        END IF;

    ELSIF v_item_type_name = 'Задание открытого типа с развернутым ответом.' THEN
        IF v_answer_text IS NULL THEN
            RAISE EXCEPTION 'Для задания типа открытый ответ open_answer_text обязателен';
        END IF;
        IF v_left_text IS NOT NULL OR v_right_text IS NOT NULL OR NEW.is_correct IS NOT NULL OR NEW.correct_order IS NOT NULL THEN
            RAISE EXCEPTION 'Для открытого ответа допускается только open_answer_text';
        END IF;

    ELSE
        RAISE EXCEPTION 'Неизвестный тип задания: %', v_item_type_name;
    END IF;

    RETURN NEW;
END;

$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_assessment_item_row_by_type
BEFORE INSERT OR UPDATE ON assessment_item_row
FOR EACH ROW
EXECUTE FUNCTION check_assessment_item_row_by_type();

COMMIT;
