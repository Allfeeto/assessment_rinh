-- Корзина образовательных программ для PostgreSQL.
-- Вариант без DO $$ блоков, чтобы его можно было выполнять целиком в psql/pgAdmin.
-- Скрипт не использует длинные имена constraint, которые PostgreSQL усекает до 63 байт.
-- Выполнять после резервной копии базы.

BEGIN;

ALTER TABLE public.educational_program
    ADD COLUMN IF NOT EXISTS is_deleted boolean;

UPDATE public.educational_program
SET is_deleted = false
WHERE is_deleted IS NULL;

ALTER TABLE public.educational_program
    ALTER COLUMN is_deleted SET DEFAULT false,
    ALTER COLUMN is_deleted SET NOT NULL;

ALTER TABLE public.educational_program
    ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone NULL;

ALTER TABLE public.educational_program
    ADD COLUMN IF NOT EXISTS deleted_by_id integer NULL;

ALTER TABLE public.educational_program
    ADD COLUMN IF NOT EXISTS delete_reason text NULL;

ALTER TABLE public.educational_program
    DROP CONSTRAINT IF EXISTS educational_program_deleted_by_fk;

ALTER TABLE public.educational_program
    ADD CONSTRAINT educational_program_deleted_by_fk
    FOREIGN KEY (deleted_by_id)
    REFERENCES public.auth_user(id)
    ON DELETE SET NULL;

-- Старое полное UNIQUE-ограничение из дампа проекта. Имя короткое и не вызывает
-- NOTICE об усечении идентификатора.
ALTER TABLE public.educational_program
    DROP CONSTRAINT IF EXISTS educational_program_program_profile_id_department_id_admiss_key;

-- На случай если в конкретной базе уже есть усеченное имя из стороннего скрипта.
ALTER TABLE public.educational_program
    DROP CONSTRAINT IF EXISTS "educational_program_program_profile_id_department_id_admission_";

DROP INDEX IF EXISTS public.educational_program_active_unique_idx;

CREATE UNIQUE INDEX educational_program_active_unique_idx
    ON public.educational_program (program_profile_id, department_id, admission_year)
    WHERE is_deleted = false;

DROP INDEX IF EXISTS public.idx_educational_program_is_deleted;

CREATE INDEX idx_educational_program_is_deleted
    ON public.educational_program (is_deleted);

DROP INDEX IF EXISTS public.idx_educational_program_deleted_at;

CREATE INDEX idx_educational_program_deleted_at
    ON public.educational_program (deleted_at);

COMMIT;
