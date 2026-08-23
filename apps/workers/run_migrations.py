"""
Aplica os ficheiros .sql em database/migrations/ que ainda não foram
aplicados, por ordem alfabética. Rastreia o que já correu numa tabela
public.schema_migrations, por isso é seguro correr isto sempre que o
container `migrate` arranca - quer a base de dados seja nova, quer já
tenha semanas de dados.

Substitui a dependência de docker-entrypoint-initdb.d (que só corre em
volumes vazios e por isso já causou dor de cabeça mais do que uma vez).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.migrate")

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "database" / "migrations"


def ensure_migrations_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                filename VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    conn.commit()


def already_applied(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT filename FROM public.schema_migrations")
        return {row[0] for row in cur.fetchall()}


def apply_migration(conn: psycopg.Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute(
            "INSERT INTO public.schema_migrations (filename) VALUES (%s)",
            (path.name,),
        )
    conn.commit()


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL não está definido")

    if not MIGRATIONS_DIR.exists():
        raise RuntimeError(f"Pasta de migrations não encontrada: {MIGRATIONS_DIR}")

    files = sorted(p for p in MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        logger.info("Nenhum ficheiro de migration encontrado em %s", MIGRATIONS_DIR)
        return

    with psycopg.connect(dsn) as conn:
        ensure_migrations_table(conn)
        applied = already_applied(conn)

        pending = [f for f in files if f.name not in applied]
        if not pending:
            logger.info("Nada para aplicar - %d migrations já correram.", len(applied))
            return

        for path in pending:
            logger.info("A aplicar %s...", path.name)
            try:
                apply_migration(conn, path)
                logger.info("OK: %s", path.name)
            except Exception:
                conn.rollback()
                logger.exception("FALHOU: %s - a parar aqui para não saltar migrations", path.name)
                raise


if __name__ == "__main__":
    main()
