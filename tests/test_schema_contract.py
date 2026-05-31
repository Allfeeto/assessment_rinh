from core.schema_contract import check_parsed_sql_schema_contract, parse_sql_schema


def test_sql_schema_contract_parser_detects_required_objects():
    schema = parse_sql_schema(
        """
        CREATE FUNCTION public.check_assessment_item_relation_integrity() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END; $$;
        CREATE FUNCTION public.check_assessment_item_competence_relation_integrity() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END; $$;
        CREATE FUNCTION public.check_assessment_item_row_by_type() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END; $$;
        CREATE FUNCTION public.check_discipline_competence_same_program() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END; $$;
        CREATE FUNCTION public.check_program_profile_code_prefix() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END; $$;

        CREATE TABLE public.education_level (
            id integer NOT NULL,
            name text NOT NULL
        );
        CREATE TABLE public.competence_type (
            id integer NOT NULL,
            name text NOT NULL
        );
        CREATE TABLE public.assessment_item_type (
            id integer NOT NULL,
            code character varying(20) NOT NULL,
            name text NOT NULL
        );
        CREATE TABLE public.academic_degree (
            id integer NOT NULL,
            name text NOT NULL
        );
        CREATE TABLE public.academic_title (
            id integer NOT NULL,
            name text NOT NULL
        );
        CREATE TABLE public.training_direction (
            id integer NOT NULL,
            education_level_id integer NOT NULL,
            code character varying(20) NOT NULL,
            name text NOT NULL
        );
        CREATE TABLE public.program_profile (
            id integer NOT NULL,
            training_direction_id integer NOT NULL,
            code character varying(30) NOT NULL,
            name text NOT NULL
        );
        CREATE TABLE public.department (
            id integer NOT NULL,
            number character varying(20) NOT NULL,
            short_name text NOT NULL,
            full_name text NOT NULL,
            head_teacher_id integer
        );
        CREATE TABLE public.educational_program (
            id integer NOT NULL,
            program_profile_id integer NOT NULL,
            department_id integer NOT NULL,
            admission_year smallint NOT NULL,
            is_deleted boolean NOT NULL,
            deleted_at timestamp with time zone,
            deleted_by_id integer,
            delete_reason text,
            CONSTRAINT educational_program_admission_year_check CHECK (((admission_year >= 2000) AND (admission_year <= 2100)))
        );
        CREATE TABLE public.discipline (
            id integer NOT NULL,
            name text NOT NULL
        );
        CREATE TABLE public.program_discipline (
            id integer NOT NULL,
            educational_program_id integer NOT NULL,
            discipline_id integer NOT NULL,
            discipline_code character varying(50),
            department_id integer,
            is_active_in_plan boolean NOT NULL
        );
        CREATE TABLE public.competence (
            id integer NOT NULL,
            educational_program_id integer NOT NULL,
            competence_type_id integer NOT NULL,
            code text NOT NULL,
            name text NOT NULL
        );
        CREATE TABLE public.discipline_competence (
            id integer NOT NULL,
            program_discipline_id integer NOT NULL,
            competence_id integer NOT NULL
        );
        CREATE TABLE public.teacher (
            id integer NOT NULL,
            user_id integer,
            department_id integer NOT NULL,
            full_name text NOT NULL,
            academic_degree_id integer,
            academic_title_id integer
        );
        CREATE TABLE public.teacher_departments (
            id bigint NOT NULL,
            teacher_id integer NOT NULL,
            department_id integer NOT NULL
        );
        CREATE TABLE public.teacher_program_discipline (
            id integer NOT NULL,
            teacher_id integer NOT NULL,
            program_discipline_id integer NOT NULL
        );
        CREATE TABLE public.assessment_item (
            id integer NOT NULL,
            program_discipline_id integer NOT NULL,
            competence_id integer,
            assessment_item_type_id integer NOT NULL,
            prompt_text text NOT NULL,
            left_column_title text,
            right_column_title text
        );
        CREATE TABLE public.assessment_item_row (
            id integer NOT NULL,
            assessment_item_id integer NOT NULL,
            left_text text,
            right_text text,
            sort_order integer,
            correct_order integer,
            is_correct boolean,
            open_answer_text text,
            CONSTRAINT assessment_item_row_check CHECK (true),
            CONSTRAINT assessment_item_row_correct_order_check CHECK (true),
            CONSTRAINT assessment_item_row_sort_order_check CHECK (true)
        );
        CREATE TABLE public.assessment_item_competence (
            id integer NOT NULL,
            assessment_item_id integer NOT NULL,
            competence_id integer NOT NULL
        );

        CREATE UNIQUE INDEX educational_program_active_unique_idx ON public.educational_program (program_profile_id, department_id, admission_year) WHERE (is_deleted = false);
        CREATE INDEX program_disc_code_idx ON public.program_discipline (discipline_code);
        CREATE INDEX program_disc_dept_idx ON public.program_discipline (department_id);
        CREATE INDEX program_disc_prog_code_idx ON public.program_discipline (educational_program_id, discipline_code);
        CREATE INDEX program_disc_prog_active_idx ON public.program_discipline (educational_program_id, is_active_in_plan);
        CREATE UNIQUE INDEX teacher_departments_teacher_department_uidx ON public.teacher_departments (teacher_id, department_id);
        CREATE INDEX teacher_departments_teacher_idx ON public.teacher_departments (teacher_id);
        CREATE INDEX teacher_departments_department_idx ON public.teacher_departments (department_id);
        CREATE UNIQUE INDEX uq_assessment_item_row_correct_order ON public.assessment_item_row (assessment_item_id, correct_order) WHERE (correct_order IS NOT NULL);
        CREATE UNIQUE INDEX uq_assessment_item_row_sort ON public.assessment_item_row (assessment_item_id, sort_order) WHERE (sort_order IS NOT NULL);

        CREATE TRIGGER trg_check_assessment_item_relation_integrity BEFORE INSERT OR UPDATE ON public.assessment_item FOR EACH ROW EXECUTE FUNCTION public.check_assessment_item_relation_integrity();
        CREATE TRIGGER trg_check_assessment_item_competence_relation_integrity BEFORE INSERT OR UPDATE ON public.assessment_item_competence FOR EACH ROW EXECUTE FUNCTION public.check_assessment_item_competence_relation_integrity();
        CREATE TRIGGER trg_check_assessment_item_row_by_type BEFORE INSERT OR UPDATE ON public.assessment_item_row FOR EACH ROW EXECUTE FUNCTION public.check_assessment_item_row_by_type();
        CREATE TRIGGER trg_check_discipline_competence_same_program BEFORE INSERT OR UPDATE ON public.discipline_competence FOR EACH ROW EXECUTE FUNCTION public.check_discipline_competence_same_program();
        CREATE TRIGGER trg_check_program_profile_code_prefix BEFORE INSERT OR UPDATE ON public.program_profile FOR EACH ROW EXECUTE FUNCTION public.check_program_profile_code_prefix();
        """
    )

    issues = check_parsed_sql_schema_contract(schema)

    assert [issue.message for issue in issues] == []
