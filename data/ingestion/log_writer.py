"""Grava o resultado de uma corrida de ingestão em raw.ingestion_log."""
from __future__ import annotations

import psycopg

from data.ingestion.base import IngestionResult


def persist_result(dest_dsn: str, result: IngestionResult) -> None:
    with psycopg.connect(dest_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO raw.ingestion_log
                    (source, entity, status, records_processed, error_message, started_at, finished_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    result.source,
                    result.entity,
                    result.status,
                    result.records_processed,
                    result.error_message,
                    result.started_at,
                    result.finished_at,
                ),
            )
        conn.commit()
