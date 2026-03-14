-- Create a `postgres` superuser role if it does not exist (idempotent)
DO $$
BEGIN
   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
      CREATE ROLE postgres LOGIN SUPERUSER PASSWORD 'postgres';
   END IF;
END
$$;
