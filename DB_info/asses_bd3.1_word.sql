--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

-- Started on 2026-04-16 01:02:59

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 5 (class 2615 OID 80547)
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- TOC entry 5199 (class 0 OID 0)
-- Dependencies: 5
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


--
-- TOC entry 282 (class 1255 OID 80832)
-- Name: check_assessment_item_relation_integrity(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.check_assessment_item_relation_integrity() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- TOC entry 283 (class 1255 OID 80834)
-- Name: check_assessment_item_row_by_type(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.check_assessment_item_row_by_type() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_item_type_name TEXT;
    v_type_norm TEXT;
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

    v_type_norm := LOWER(REGEXP_REPLACE(BTRIM(v_item_type_name), '\\s+', ' ', 'g'));

    IF v_type_norm LIKE '%выбор%одного%верного%' OR v_type_norm = 'выбор одного ответа' THEN
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

    ELSIF v_type_norm LIKE '%выбор%нескольк%' OR v_type_norm = 'выбор нескольких ответов' THEN
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

    ELSIF v_type_norm LIKE '%соответств%' OR v_type_norm = 'установление соответствия' THEN
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

    ELSIF v_type_norm LIKE '%последоват%' OR v_type_norm = 'установление последовательности' THEN
        IF v_left_text IS NULL THEN
            RAISE EXCEPTION 'Для задания на последовательность left_text обязателен';
        END IF;
        IF NEW.correct_order IS NULL THEN
            RAISE EXCEPTION 'Для задания на последовательность correct_order обязателен';
        END IF;
        IF v_right_text IS NOT NULL OR v_answer_text IS NOT NULL OR NEW.is_correct IS NOT NULL THEN
            RAISE EXCEPTION 'Для задания на последовательность допускаются только left_text, sort_order, correct_order';
        END IF;

    ELSIF v_type_norm LIKE '%открыт%' OR v_type_norm = 'открытый ответ' THEN
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
$$;


--
-- TOC entry 269 (class 1255 OID 80828)
-- Name: check_department_head_teacher(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.check_department_head_teacher() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- TOC entry 281 (class 1255 OID 80830)
-- Name: check_discipline_competence_same_program(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.check_discipline_competence_same_program() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- TOC entry 268 (class 1255 OID 80826)
-- Name: check_program_profile_code_prefix(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.check_program_profile_code_prefix() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
$$;


SET default_table_access_method = heap;

--
-- TOC entry 224 (class 1259 OID 80582)
-- Name: academic_degree; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.academic_degree (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- TOC entry 223 (class 1259 OID 80581)
-- Name: academic_degree_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.academic_degree_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5200 (class 0 OID 0)
-- Dependencies: 223
-- Name: academic_degree_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.academic_degree_id_seq OWNED BY public.academic_degree.id;


--
-- TOC entry 226 (class 1259 OID 80593)
-- Name: academic_title; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.academic_title (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- TOC entry 225 (class 1259 OID 80592)
-- Name: academic_title_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.academic_title_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5201 (class 0 OID 0)
-- Dependencies: 225
-- Name: academic_title_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.academic_title_id_seq OWNED BY public.academic_title.id;


--
-- TOC entry 246 (class 1259 OID 80768)
-- Name: assessment_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_item (
    id integer NOT NULL,
    program_discipline_id integer NOT NULL,
    competence_id integer NOT NULL,
    assessment_item_type_id integer NOT NULL,
    prompt_text text NOT NULL,
    left_column_title text,
    right_column_title text
);


--
-- TOC entry 245 (class 1259 OID 80767)
-- Name: assessment_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assessment_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5202 (class 0 OID 0)
-- Dependencies: 245
-- Name: assessment_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assessment_item_id_seq OWNED BY public.assessment_item.id;


--
-- TOC entry 248 (class 1259 OID 80792)
-- Name: assessment_item_row; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_item_row (
    id integer NOT NULL,
    assessment_item_id integer NOT NULL,
    left_text text,
    right_text text,
    sort_order integer,
    correct_order integer,
    is_correct boolean,
    open_answer_text text,
    CONSTRAINT assessment_item_row_check CHECK (((NULLIF(btrim(COALESCE(left_text, ''::text)), ''::text) IS NOT NULL) OR (NULLIF(btrim(COALESCE(right_text, ''::text)), ''::text) IS NOT NULL) OR (NULLIF(btrim(COALESCE(open_answer_text, ''::text)), ''::text) IS NOT NULL))),
    CONSTRAINT assessment_item_row_correct_order_check CHECK (((correct_order IS NULL) OR (correct_order > 0))),
    CONSTRAINT assessment_item_row_sort_order_check CHECK (((sort_order IS NULL) OR (sort_order > 0)))
);


--
-- TOC entry 247 (class 1259 OID 80791)
-- Name: assessment_item_row_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assessment_item_row_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5203 (class 0 OID 0)
-- Dependencies: 247
-- Name: assessment_item_row_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assessment_item_row_id_seq OWNED BY public.assessment_item_row.id;


--
-- TOC entry 222 (class 1259 OID 80571)
-- Name: assessment_item_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_item_type (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- TOC entry 221 (class 1259 OID 80570)
-- Name: assessment_item_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assessment_item_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5204 (class 0 OID 0)
-- Dependencies: 221
-- Name: assessment_item_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assessment_item_type_id_seq OWNED BY public.assessment_item_type.id;


--
-- TOC entry 256 (class 1259 OID 80860)
-- Name: auth_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


--
-- TOC entry 255 (class 1259 OID 80859)
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 258 (class 1259 OID 80868)
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- TOC entry 257 (class 1259 OID 80867)
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_group_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 254 (class 1259 OID 80854)
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


--
-- TOC entry 253 (class 1259 OID 80853)
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_permission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 260 (class 1259 OID 80874)
-- Name: auth_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);


--
-- TOC entry 262 (class 1259 OID 80882)
-- Name: auth_user_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_user_groups (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


--
-- TOC entry 261 (class 1259 OID 80881)
-- Name: auth_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_user_groups ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 259 (class 1259 OID 80873)
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_user ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 264 (class 1259 OID 80888)
-- Name: auth_user_user_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_user_user_permissions (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- TOC entry 263 (class 1259 OID 80887)
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_user_user_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 242 (class 1259 OID 80728)
-- Name: competence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.competence (
    id integer NOT NULL,
    educational_program_id integer NOT NULL,
    competence_type_id integer NOT NULL,
    code text NOT NULL,
    name text NOT NULL
);


--
-- TOC entry 241 (class 1259 OID 80727)
-- Name: competence_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.competence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5205 (class 0 OID 0)
-- Dependencies: 241
-- Name: competence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.competence_id_seq OWNED BY public.competence.id;


--
-- TOC entry 220 (class 1259 OID 80560)
-- Name: competence_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.competence_type (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- TOC entry 219 (class 1259 OID 80559)
-- Name: competence_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.competence_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5206 (class 0 OID 0)
-- Dependencies: 219
-- Name: competence_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.competence_type_id_seq OWNED BY public.competence_type.id;


--
-- TOC entry 228 (class 1259 OID 80604)
-- Name: department; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.department (
    id integer NOT NULL,
    number character varying(20) NOT NULL,
    short_name text NOT NULL,
    full_name text NOT NULL,
    head_teacher_id integer
);


--
-- TOC entry 227 (class 1259 OID 80603)
-- Name: department_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.department_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5207 (class 0 OID 0)
-- Dependencies: 227
-- Name: department_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.department_id_seq OWNED BY public.department.id;


--
-- TOC entry 238 (class 1259 OID 80698)
-- Name: discipline; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.discipline (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- TOC entry 244 (class 1259 OID 80749)
-- Name: discipline_competence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.discipline_competence (
    id integer NOT NULL,
    program_discipline_id integer NOT NULL,
    competence_id integer NOT NULL
);


--
-- TOC entry 243 (class 1259 OID 80748)
-- Name: discipline_competence_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.discipline_competence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5208 (class 0 OID 0)
-- Dependencies: 243
-- Name: discipline_competence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.discipline_competence_id_seq OWNED BY public.discipline_competence.id;


--
-- TOC entry 237 (class 1259 OID 80697)
-- Name: discipline_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.discipline_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5209 (class 0 OID 0)
-- Dependencies: 237
-- Name: discipline_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.discipline_id_seq OWNED BY public.discipline.id;


--
-- TOC entry 266 (class 1259 OID 80946)
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


--
-- TOC entry 265 (class 1259 OID 80945)
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.django_admin_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 252 (class 1259 OID 80846)
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


--
-- TOC entry 251 (class 1259 OID 80845)
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.django_content_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 250 (class 1259 OID 80838)
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_migrations (
    id bigint NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


--
-- TOC entry 249 (class 1259 OID 80837)
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.django_migrations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 267 (class 1259 OID 80974)
-- Name: django_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


--
-- TOC entry 218 (class 1259 OID 80549)
-- Name: education_level; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.education_level (
    id integer NOT NULL,
    name text NOT NULL
);


--
-- TOC entry 217 (class 1259 OID 80548)
-- Name: education_level_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.education_level_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5210 (class 0 OID 0)
-- Dependencies: 217
-- Name: education_level_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.education_level_id_seq OWNED BY public.education_level.id;


--
-- TOC entry 236 (class 1259 OID 80678)
-- Name: educational_program; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.educational_program (
    id integer NOT NULL,
    program_profile_id integer NOT NULL,
    department_id integer NOT NULL,
    admission_year smallint NOT NULL,
    CONSTRAINT educational_program_admission_year_check CHECK (((admission_year >= 2000) AND (admission_year <= 2100)))
);


--
-- TOC entry 235 (class 1259 OID 80677)
-- Name: educational_program_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.educational_program_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5211 (class 0 OID 0)
-- Dependencies: 235
-- Name: educational_program_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.educational_program_id_seq OWNED BY public.educational_program.id;


--
-- TOC entry 240 (class 1259 OID 80709)
-- Name: program_discipline; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.program_discipline (
    id integer NOT NULL,
    educational_program_id integer NOT NULL,
    discipline_id integer NOT NULL
);


--
-- TOC entry 239 (class 1259 OID 80708)
-- Name: program_discipline_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.program_discipline_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5212 (class 0 OID 0)
-- Dependencies: 239
-- Name: program_discipline_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.program_discipline_id_seq OWNED BY public.program_discipline.id;


--
-- TOC entry 234 (class 1259 OID 80660)
-- Name: program_profile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.program_profile (
    id integer NOT NULL,
    training_direction_id integer NOT NULL,
    code character varying(30) NOT NULL,
    name text NOT NULL
);


--
-- TOC entry 233 (class 1259 OID 80659)
-- Name: program_profile_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.program_profile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5213 (class 0 OID 0)
-- Dependencies: 233
-- Name: program_profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.program_profile_id_seq OWNED BY public.program_profile.id;


--
-- TOC entry 230 (class 1259 OID 80615)
-- Name: teacher; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher (
    id integer NOT NULL,
    department_id integer NOT NULL,
    full_name text NOT NULL,
    academic_degree_id integer,
    academic_title_id integer
);


--
-- TOC entry 229 (class 1259 OID 80614)
-- Name: teacher_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5214 (class 0 OID 0)
-- Dependencies: 229
-- Name: teacher_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_id_seq OWNED BY public.teacher.id;


--
-- TOC entry 232 (class 1259 OID 80644)
-- Name: training_direction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.training_direction (
    id integer NOT NULL,
    education_level_id integer NOT NULL,
    code character varying(20) NOT NULL,
    name text NOT NULL
);


--
-- TOC entry 231 (class 1259 OID 80643)
-- Name: training_direction_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.training_direction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5215 (class 0 OID 0)
-- Dependencies: 231
-- Name: training_direction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.training_direction_id_seq OWNED BY public.training_direction.id;


--
-- TOC entry 4874 (class 2604 OID 80585)
-- Name: academic_degree id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.academic_degree ALTER COLUMN id SET DEFAULT nextval('public.academic_degree_id_seq'::regclass);


--
-- TOC entry 4875 (class 2604 OID 80596)
-- Name: academic_title id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.academic_title ALTER COLUMN id SET DEFAULT nextval('public.academic_title_id_seq'::regclass);


--
-- TOC entry 4885 (class 2604 OID 80771)
-- Name: assessment_item id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_item ALTER COLUMN id SET DEFAULT nextval('public.assessment_item_id_seq'::regclass);


--
-- TOC entry 4886 (class 2604 OID 80795)
-- Name: assessment_item_row id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_item_row ALTER COLUMN id SET DEFAULT nextval('public.assessment_item_row_id_seq'::regclass);


--
-- TOC entry 4873 (class 2604 OID 80574)
-- Name: assessment_item_type id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_item_type ALTER COLUMN id SET DEFAULT nextval('public.assessment_item_type_id_seq'::regclass);


--
-- TOC entry 4883 (class 2604 OID 80731)
-- Name: competence id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competence ALTER COLUMN id SET DEFAULT nextval('public.competence_id_seq'::regclass);


--
-- TOC entry 4872 (class 2604 OID 80563)
-- Name: competence_type id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competence_type ALTER COLUMN id SET DEFAULT nextval('public.competence_type_id_seq'::regclass);


--
-- TOC entry 4876 (class 2604 OID 80607)
-- Name: department id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department ALTER COLUMN id SET DEFAULT nextval('public.department_id_seq'::regclass);


--
-- TOC entry 4881 (class 2604 OID 80701)
-- Name: discipline id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discipline ALTER COLUMN id SET DEFAULT nextval('public.discipline_id_seq'::regclass);


--
-- TOC entry 4884 (class 2604 OID 80752)
-- Name: discipline_competence id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discipline_competence ALTER COLUMN id SET DEFAULT nextval('public.discipline_competence_id_seq'::regclass);


--
-- TOC entry 4871 (class 2604 OID 80552)
-- Name: education_level id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.education_level ALTER COLUMN id SET DEFAULT nextval('public.education_level_id_seq'::regclass);


--
-- TOC entry 4880 (class 2604 OID 80681)
-- Name: educational_program id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.educational_program ALTER COLUMN id SET DEFAULT nextval('public.educational_program_id_seq'::regclass);


--
-- TOC entry 4882 (class 2604 OID 80712)
-- Name: program_discipline id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.program_discipline ALTER COLUMN id SET DEFAULT nextval('public.program_discipline_id_seq'::regclass);


--
-- TOC entry 4879 (class 2604 OID 80663)
-- Name: program_profile id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.program_profile ALTER COLUMN id SET DEFAULT nextval('public.program_profile_id_seq'::regclass);


--
-- TOC entry 4877 (class 2604 OID 80618)
-- Name: teacher id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher ALTER COLUMN id SET DEFAULT nextval('public.teacher_id_seq'::regclass);


--
-- TOC entry 4878 (class 2604 OID 80647)
-- Name: training_direction id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_direction ALTER COLUMN id SET DEFAULT nextval('public.training_direction_id_seq'::regclass);


--
-- TOC entry 4905 (class 2606 OID 80591)
-- Name: academic_degree academic_degree_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.academic_degree
    ADD CONSTRAINT academic_degree_name_key UNIQUE (name);


--
-- TOC entry 4907 (class 2606 OID 80589)
-- Name: academic_degree academic_degree_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.academic_degree
    ADD CONSTRAINT academic_degree_pkey PRIMARY KEY (id);


--
-- TOC entry 4909 (class 2606 OID 80602)
-- Name: academic_title academic_title_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.academic_title
    ADD CONSTRAINT academic_title_name_key UNIQUE (name);


--
-- TOC entry 4911 (class 2606 OID 80600)
-- Name: academic_title academic_title_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.academic_title
    ADD CONSTRAINT academic_title_pkey PRIMARY KEY (id);


--
-- TOC entry 4961 (class 2606 OID 80775)
-- Name: assessment_item assessment_item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_item
    ADD CONSTRAINT assessment_item_pkey PRIMARY KEY (id);


--
-- TOC entry 4966 (class 2606 OID 80802)
-- Name: assessment_item_row assessment_item_row_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_item_row
    ADD CONSTRAINT assessment_item_row_pkey PRIMARY KEY (id);


--
-- TOC entry 4901 (class 2606 OID 80580)
-- Name: assessment_item_type assessment_item_type_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_item_type
    ADD CONSTRAINT assessment_item_type_name_key UNIQUE (name);


--
-- TOC entry 4903 (class 2606 OID 80578)
-- Name: assessment_item_type assessment_item_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_item_type
    ADD CONSTRAINT assessment_item_type_pkey PRIMARY KEY (id);


--
-- TOC entry 4983 (class 2606 OID 80972)
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- TOC entry 4988 (class 2606 OID 80903)
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- TOC entry 4991 (class 2606 OID 80872)
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- TOC entry 4985 (class 2606 OID 80864)
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- TOC entry 4978 (class 2606 OID 80894)
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- TOC entry 4980 (class 2606 OID 80858)
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- TOC entry 4999 (class 2606 OID 80886)
-- Name: auth_user_groups auth_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);


--
-- TOC entry 5002 (class 2606 OID 80918)
-- Name: auth_user_groups auth_user_groups_user_id_group_id_94350c0c_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);


--
-- TOC entry 4993 (class 2606 OID 80878)
-- Name: auth_user auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- TOC entry 5005 (class 2606 OID 80892)
-- Name: auth_user_user_permissions auth_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);


--
-- TOC entry 5008 (class 2606 OID 80932)
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_permission_id_14a6b632_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);


--
-- TOC entry 4996 (class 2606 OID 80967)
-- Name: auth_user auth_user_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);


--
-- TOC entry 4949 (class 2606 OID 80737)
-- Name: competence competence_educational_program_id_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competence
    ADD CONSTRAINT competence_educational_program_id_code_key UNIQUE (educational_program_id, code);


--
-- TOC entry 4951 (class 2606 OID 80735)
-- Name: competence competence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competence
    ADD CONSTRAINT competence_pkey PRIMARY KEY (id);


--
-- TOC entry 4897 (class 2606 OID 80569)
-- Name: competence_type competence_type_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competence_type
    ADD CONSTRAINT competence_type_name_key UNIQUE (name);


--
-- TOC entry 4899 (class 2606 OID 80567)
-- Name: competence_type competence_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competence_type
    ADD CONSTRAINT competence_type_pkey PRIMARY KEY (id);


--
-- TOC entry 4913 (class 2606 OID 80613)
-- Name: department department_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department
    ADD CONSTRAINT department_number_key UNIQUE (number);


--
-- TOC entry 4915 (class 2606 OID 80611)
-- Name: department department_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department
    ADD CONSTRAINT department_pkey PRIMARY KEY (id);


--
-- TOC entry 4955 (class 2606 OID 80754)
-- Name: discipline_competence discipline_competence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discipline_competence
    ADD CONSTRAINT discipline_competence_pkey PRIMARY KEY (id);


--
-- TOC entry 4957 (class 2606 OID 80756)
-- Name: discipline_competence discipline_competence_program_discipline_id_competence_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discipline_competence
    ADD CONSTRAINT discipline_competence_program_discipline_id_competence_id_key UNIQUE (program_discipline_id, competence_id);


--
-- TOC entry 4939 (class 2606 OID 80707)
-- Name: discipline discipline_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discipline
    ADD CONSTRAINT discipline_name_key UNIQUE (name);


--
-- TOC entry 4941 (class 2606 OID 80705)
-- Name: discipline discipline_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discipline
    ADD CONSTRAINT discipline_pkey PRIMARY KEY (id);


--
-- TOC entry 5011 (class 2606 OID 80953)
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- TOC entry 4973 (class 2606 OID 80852)
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- TOC entry 4975 (class 2606 OID 80850)
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- TOC entry 4971 (class 2606 OID 80844)
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- TOC entry 5015 (class 2606 OID 80980)
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- TOC entry 4893 (class 2606 OID 80558)
-- Name: education_level education_level_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.education_level
    ADD CONSTRAINT education_level_name_key UNIQUE (name);


--
-- TOC entry 4895 (class 2606 OID 80556)
-- Name: education_level education_level_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.education_level
    ADD CONSTRAINT education_level_pkey PRIMARY KEY (id);


--
-- TOC entry 4933 (class 2606 OID 80684)
-- Name: educational_program educational_program_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.educational_program
    ADD CONSTRAINT educational_program_pkey PRIMARY KEY (id);


--
-- TOC entry 4935 (class 2606 OID 80686)
-- Name: educational_program educational_program_program_profile_id_department_id_admiss_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.educational_program
    ADD CONSTRAINT educational_program_program_profile_id_department_id_admiss_key UNIQUE (program_profile_id, department_id, admission_year);


--
-- TOC entry 4945 (class 2606 OID 80716)
-- Name: program_discipline program_discipline_educational_program_id_discipline_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.program_discipline
    ADD CONSTRAINT program_discipline_educational_program_id_discipline_id_key UNIQUE (educational_program_id, discipline_id);


--
-- TOC entry 4947 (class 2606 OID 80714)
-- Name: program_discipline program_discipline_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.program_discipline
    ADD CONSTRAINT program_discipline_pkey PRIMARY KEY (id);


--
-- TOC entry 4927 (class 2606 OID 80669)
-- Name: program_profile program_profile_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.program_profile
    ADD CONSTRAINT program_profile_code_key UNIQUE (code);


--
-- TOC entry 4929 (class 2606 OID 80667)
-- Name: program_profile program_profile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.program_profile
    ADD CONSTRAINT program_profile_pkey PRIMARY KEY (id);


--
-- TOC entry 4931 (class 2606 OID 80671)
-- Name: program_profile program_profile_training_direction_id_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.program_profile
    ADD CONSTRAINT program_profile_training_direction_id_name_key UNIQUE (training_direction_id, name);


--
-- TOC entry 4919 (class 2606 OID 80622)
-- Name: teacher teacher_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher
    ADD CONSTRAINT teacher_pkey PRIMARY KEY (id);


--
-- TOC entry 4922 (class 2606 OID 80653)
-- Name: training_direction training_direction_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_direction
    ADD CONSTRAINT training_direction_code_key UNIQUE (code);


--
-- TOC entry 4924 (class 2606 OID 80651)
-- Name: training_direction training_direction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_direction
    ADD CONSTRAINT training_direction_pkey PRIMARY KEY (id);


--
-- TOC entry 4981 (class 1259 OID 80973)
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- TOC entry 4986 (class 1259 OID 80914)
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- TOC entry 4989 (class 1259 OID 80915)
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- TOC entry 4976 (class 1259 OID 80900)
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- TOC entry 4997 (class 1259 OID 80930)
-- Name: auth_user_groups_group_id_97559544; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id);


--
-- TOC entry 5000 (class 1259 OID 80929)
-- Name: auth_user_groups_user_id_6a12ed8b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id);


--
-- TOC entry 5003 (class 1259 OID 80944)
-- Name: auth_user_user_permissions_permission_id_1fbb5f2c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id);


--
-- TOC entry 5006 (class 1259 OID 80943)
-- Name: auth_user_user_permissions_user_id_a95ead1b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id);


--
-- TOC entry 4994 (class 1259 OID 80968)
-- Name: auth_user_username_6821ab7c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops);


--
-- TOC entry 5009 (class 1259 OID 80964)
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- TOC entry 5012 (class 1259 OID 80965)
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- TOC entry 5013 (class 1259 OID 80982)
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- TOC entry 5016 (class 1259 OID 80981)
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- TOC entry 4962 (class 1259 OID 80824)
-- Name: idx_assessment_item_assessment_item_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_assessment_item_assessment_item_type_id ON public.assessment_item USING btree (assessment_item_type_id);


--
-- TOC entry 4963 (class 1259 OID 80823)
-- Name: idx_assessment_item_competence_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_assessment_item_competence_id ON public.assessment_item USING btree (competence_id);


--
-- TOC entry 4964 (class 1259 OID 80822)
-- Name: idx_assessment_item_program_discipline_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_assessment_item_program_discipline_id ON public.assessment_item USING btree (program_discipline_id);


--
-- TOC entry 4967 (class 1259 OID 80825)
-- Name: idx_assessment_item_row_assessment_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_assessment_item_row_assessment_item_id ON public.assessment_item_row USING btree (assessment_item_id);


--
-- TOC entry 4952 (class 1259 OID 80819)
-- Name: idx_competence_competence_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_competence_competence_type_id ON public.competence USING btree (competence_type_id);


--
-- TOC entry 4953 (class 1259 OID 80818)
-- Name: idx_competence_educational_program_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_competence_educational_program_id ON public.competence USING btree (educational_program_id);


--
-- TOC entry 4916 (class 1259 OID 80811)
-- Name: idx_department_head_teacher_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_department_head_teacher_id ON public.department USING btree (head_teacher_id);


--
-- TOC entry 4958 (class 1259 OID 80821)
-- Name: idx_discipline_competence_competence_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_discipline_competence_competence_id ON public.discipline_competence USING btree (competence_id);


--
-- TOC entry 4959 (class 1259 OID 80820)
-- Name: idx_discipline_competence_program_discipline_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_discipline_competence_program_discipline_id ON public.discipline_competence USING btree (program_discipline_id);


--
-- TOC entry 4936 (class 1259 OID 80815)
-- Name: idx_educational_program_department_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_educational_program_department_id ON public.educational_program USING btree (department_id);


--
-- TOC entry 4937 (class 1259 OID 80814)
-- Name: idx_educational_program_program_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_educational_program_program_profile_id ON public.educational_program USING btree (program_profile_id);


--
-- TOC entry 4942 (class 1259 OID 80817)
-- Name: idx_program_discipline_discipline_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_program_discipline_discipline_id ON public.program_discipline USING btree (discipline_id);


--
-- TOC entry 4943 (class 1259 OID 80816)
-- Name: idx_program_discipline_educational_program_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_program_discipline_educational_program_id ON public.program_discipline USING btree (educational_program_id);


--
-- TOC entry 4925 (class 1259 OID 80813)
-- Name: idx_program_profile_training_direction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_program_profile_training_direction_id ON public.program_profile USING btree (training_direction_id);


--
-- TOC entry 4917 (class 1259 OID 80810)
-- Name: idx_teacher_department_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_teacher_department_id ON public.teacher USING btree (department_id);


--
-- TOC entry 4920 (class 1259 OID 80812)
-- Name: idx_training_direction_education_level_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_direction_education_level_id ON public.training_direction USING btree (education_level_id);


--
-- TOC entry 4968 (class 1259 OID 80809)
-- Name: uq_assessment_item_row_correct_order; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_assessment_item_row_correct_order ON public.assessment_item_row USING btree (assessment_item_id, correct_order) WHERE (correct_order IS NOT NULL);


--
-- TOC entry 4969 (class 1259 OID 80808)
-- Name: uq_assessment_item_row_sort; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_assessment_item_row_sort ON public.assessment_item_row USING btree (assessment_item_id, sort_order) WHERE (sort_order IS NOT NULL);


--
-- TOC entry 5047 (class 2620 OID 80833)
-- Name: assessment_item trg_check_assessment_item_relation_integrity; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_check_assessment_item_relation_integrity BEFORE INSERT OR UPDATE ON public.assessment_item FOR EACH ROW EXECUTE FUNCTION public.check_assessment_item_relation_integrity();


--
-- TOC entry 5048 (class 2620 OID 80835)
-- Name: assessment_item_row trg_check_assessment_item_row_by_type; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_check_assessment_item_row_by_type BEFORE INSERT OR UPDATE ON public.assessment_item_row FOR EACH ROW EXECUTE FUNCTION public.check_assessment_item_row_by_type();


--
-- TOC entry 5044 (class 2620 OID 80829)
-- Name: department trg_check_department_head_teacher; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_check_department_head_teacher BEFORE INSERT OR UPDATE ON public.department FOR EACH ROW EXECUTE FUNCTION public.check_department_head_teacher();


--
-- TOC entry 5046 (class 2620 OID 80831)
-- Name: discipline_competence trg_check_discipline_competence_same_program; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_check_discipline_competence_same_program BEFORE INSERT OR UPDATE ON public.discipline_competence FOR EACH ROW EXECUTE FUNCTION public.check_discipline_competence_same_program();


--
-- TOC entry 5045 (class 2620 OID 80827)
-- Name: program_profile trg_check_program_profile_code_prefix; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_check_program_profile_code_prefix BEFORE INSERT OR UPDATE ON public.program_profile FOR EACH ROW EXECUTE FUNCTION public.check_program_profile_code_prefix();


--
-- TOC entry 5031 (class 2606 OID 80786)
-- Name: assessment_item assessment_item_assessment_item_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_item
    ADD CONSTRAINT assessment_item_assessment_item_type_id_fkey FOREIGN KEY (assessment_item_type_id) REFERENCES public.assessment_item_type(id) ON DELETE RESTRICT;


--
-- TOC entry 5032 (class 2606 OID 80781)
-- Name: assessment_item assessment_item_competence_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_item
    ADD CONSTRAINT assessment_item_competence_id_fkey FOREIGN KEY (competence_id) REFERENCES public.competence(id) ON DELETE RESTRICT;


--
-- TOC entry 5033 (class 2606 OID 80776)
-- Name: assessment_item assessment_item_program_discipline_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_item
    ADD CONSTRAINT assessment_item_program_discipline_id_fkey FOREIGN KEY (program_discipline_id) REFERENCES public.program_discipline(id) ON DELETE CASCADE;


--
-- TOC entry 5034 (class 2606 OID 80803)
-- Name: assessment_item_row assessment_item_row_assessment_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_item_row
    ADD CONSTRAINT assessment_item_row_assessment_item_id_fkey FOREIGN KEY (assessment_item_id) REFERENCES public.assessment_item(id) ON DELETE CASCADE;


--
-- TOC entry 5036 (class 2606 OID 80909)
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 5037 (class 2606 OID 80904)
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 5035 (class 2606 OID 80895)
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 5038 (class 2606 OID 80924)
-- Name: auth_user_groups auth_user_groups_group_id_97559544_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 5039 (class 2606 OID 80919)
-- Name: auth_user_groups auth_user_groups_user_id_6a12ed8b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 5040 (class 2606 OID 80938)
-- Name: auth_user_user_permissions auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 5041 (class 2606 OID 80933)
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 5027 (class 2606 OID 80743)
-- Name: competence competence_competence_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competence
    ADD CONSTRAINT competence_competence_type_id_fkey FOREIGN KEY (competence_type_id) REFERENCES public.competence_type(id) ON DELETE RESTRICT;


--
-- TOC entry 5028 (class 2606 OID 80738)
-- Name: competence competence_educational_program_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competence
    ADD CONSTRAINT competence_educational_program_id_fkey FOREIGN KEY (educational_program_id) REFERENCES public.educational_program(id) ON DELETE CASCADE;


--
-- TOC entry 5017 (class 2606 OID 80638)
-- Name: department department_head_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department
    ADD CONSTRAINT department_head_teacher_id_fkey FOREIGN KEY (head_teacher_id) REFERENCES public.teacher(id) ON DELETE RESTRICT;


--
-- TOC entry 5029 (class 2606 OID 80762)
-- Name: discipline_competence discipline_competence_competence_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discipline_competence
    ADD CONSTRAINT discipline_competence_competence_id_fkey FOREIGN KEY (competence_id) REFERENCES public.competence(id) ON DELETE CASCADE;


--
-- TOC entry 5030 (class 2606 OID 80757)
-- Name: discipline_competence discipline_competence_program_discipline_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discipline_competence
    ADD CONSTRAINT discipline_competence_program_discipline_id_fkey FOREIGN KEY (program_discipline_id) REFERENCES public.program_discipline(id) ON DELETE CASCADE;


--
-- TOC entry 5042 (class 2606 OID 80954)
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 5043 (class 2606 OID 80959)
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 5023 (class 2606 OID 80692)
-- Name: educational_program educational_program_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.educational_program
    ADD CONSTRAINT educational_program_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.department(id) ON DELETE RESTRICT;


--
-- TOC entry 5024 (class 2606 OID 80687)
-- Name: educational_program educational_program_program_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.educational_program
    ADD CONSTRAINT educational_program_program_profile_id_fkey FOREIGN KEY (program_profile_id) REFERENCES public.program_profile(id) ON DELETE RESTRICT;


--
-- TOC entry 5025 (class 2606 OID 80722)
-- Name: program_discipline program_discipline_discipline_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.program_discipline
    ADD CONSTRAINT program_discipline_discipline_id_fkey FOREIGN KEY (discipline_id) REFERENCES public.discipline(id) ON DELETE RESTRICT;


--
-- TOC entry 5026 (class 2606 OID 80717)
-- Name: program_discipline program_discipline_educational_program_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.program_discipline
    ADD CONSTRAINT program_discipline_educational_program_id_fkey FOREIGN KEY (educational_program_id) REFERENCES public.educational_program(id) ON DELETE CASCADE;


--
-- TOC entry 5022 (class 2606 OID 80672)
-- Name: program_profile program_profile_training_direction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.program_profile
    ADD CONSTRAINT program_profile_training_direction_id_fkey FOREIGN KEY (training_direction_id) REFERENCES public.training_direction(id) ON DELETE CASCADE;


--
-- TOC entry 5018 (class 2606 OID 80628)
-- Name: teacher teacher_academic_degree_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher
    ADD CONSTRAINT teacher_academic_degree_id_fkey FOREIGN KEY (academic_degree_id) REFERENCES public.academic_degree(id) ON DELETE RESTRICT;


--
-- TOC entry 5019 (class 2606 OID 80633)
-- Name: teacher teacher_academic_title_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher
    ADD CONSTRAINT teacher_academic_title_id_fkey FOREIGN KEY (academic_title_id) REFERENCES public.academic_title(id) ON DELETE RESTRICT;


--
-- TOC entry 5020 (class 2606 OID 80623)
-- Name: teacher teacher_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher
    ADD CONSTRAINT teacher_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.department(id) ON DELETE RESTRICT;


--
-- TOC entry 5021 (class 2606 OID 80654)
-- Name: training_direction training_direction_education_level_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_direction
    ADD CONSTRAINT training_direction_education_level_id_fkey FOREIGN KEY (education_level_id) REFERENCES public.education_level(id) ON DELETE RESTRICT;


-- Completed on 2026-04-16 01:02:59

--
-- PostgreSQL database dump complete
--

