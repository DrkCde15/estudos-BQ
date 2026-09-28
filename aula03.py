"""Aula 03 — Query jobs: SELECT, dry run e parâmetros.

Objetivo: rodar SELECT sem surpresa de custo no sandbox.
- dry_run=True estima bytes antes de executar (grátis, não consome cota).
- Query parametrizada evita SQL injection e reaproveita cache.
- SELECT sobre staging.biq_copy (tabela das aulas 01/02).

Equivalentes bq CLI:
  bq query --dry_run --project_id=engdta 'SELECT keep_me FROM `engdta.staging.biq_copy` LIMIT 10'
  bq query --project_id=engdta --parameter=prefix:STRING:keep 'SELECT * FROM `engdta.staging.biq_copy` WHERE keep_me LIKE @prefix LIMIT 10'
"""

import os

from google.api_core import exceptions
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT", "engdta")
FULL_TABLE_ID = f"{PROJECT_ID}.staging.biq_copy"


def estimate_bytes(client: bigquery.Client, sql: str) -> int | None:
    """Roda dry run e retorna bytes estimados (None se falhar)."""
    try:
        job = client.query(
            sql,
            job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
        )
        print(f"Dry run: ~{job.total_bytes_processed} bytes (~{job.total_bytes_processed / 1e9:.4f} GB)")
        return job.total_bytes_processed
    except exceptions.Forbidden as e:
        print(f"Dry run bloqueado (sandbox?): {e}")
        return None


def run_select_all(client: bigquery.Client, limit: int = 10) -> None:
    sql = f"SELECT * FROM `{FULL_TABLE_ID}` LIMIT {int(limit)}"
    estimate_bytes(client, sql)
    try:
        rows = list(client.query(sql).result(timeout=60))
    except exceptions.NotFound:
        print(f"Tabela {FULL_TABLE_ID} não existe ainda — rode a aula02 primeiro.")
        return
    except exceptions.Forbidden as e:
        print(f"SELECT bloqueado: {e}")
        return
    print(f"{len(rows)} linha(s):")
    for row in rows:
        print(dict(row))


def run_param_query(client: bigquery.Client, prefix: str = "keep") -> None:
    """Exemplo de query parametrizada (usa índice/cache melhor que f-string)."""
    sql = f"SELECT keep_me FROM `{FULL_TABLE_ID}` WHERE keep_me LIKE @prefix LIMIT 10"
    estimate_bytes(client, sql)
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("prefix", "STRING", f"{prefix}%")]
    )
    try:
        rows = list(client.query(sql, job_config=job_config).result(timeout=60))
    except (exceptions.NotFound, exceptions.BadRequest) as e:
        # BadRequest: coluna keep_me ainda não existe (aula02 não rodou o ensure).
        print(f"Query parametrizada pulada: {e}")
        return
    print(f"Param query (@prefix={prefix}%): {len(rows)} linha(s).")


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    run_select_all(client)
    run_param_query(client)


if __name__ == "__main__":
    main()
