"""Aula 05 — Ingestão batch (permitida no sandbox) vs streaming (bloqueada).

Objetivo: mostrar o caminho que funciona sem billing.
- insert_rows_json (streaming insertAll) → 403 no sandbox (visto na aula02).
- load_table_from_json (load job batch) → permitido, com WRITE_TRUNCATE idempotente.
- WRITE_TRUNCATE: re-run substitui tudo (mesmo resultado final).

Equivalentes bq CLI:
  bq load --source_format=NEWLINE_DELIMITED_JSON --project_id=engdta engdta:staging.aula05_batch ./aula05_rows.json
  bq show --project_id=engdta engdta:staging.aula05_batch
"""

import os

from google.api_core import exceptions
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT", "engdta")
DATASET_ID = "staging"
TABLE_ID = "aula05_batch"
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

ROWS = [
    {"id": 1, "nome": "ada", "ativo": True},
    {"id": 2, "nome": "grace", "ativo": False},
]

SCHEMA = [
    bigquery.SchemaField("id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("nome", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("ativo", "BOOL", mode="NULLABLE"),
]


def batch_load(client: bigquery.Client) -> None:
    """Carga batch idempotente (TRUNCATE): re-run não duplica."""
    dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
    client.create_dataset(bigquery.Dataset(dataset_ref), exists_ok=True)
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    try:
        job = client.load_table_from_json(ROWS, FULL_TABLE_ID, job_config=job_config)
        job.result(timeout=120)
    except exceptions.Forbidden as e:
        print(f"LOAD pulado (sandbox/billing): {e}")
        return
    table = client.get_table(FULL_TABLE_ID)
    print(f"LOAD batch OK: {table.num_rows} linha(s) em {FULL_TABLE_ID} (TRUNCATE).")


def show_rows(client: bigquery.Client, limit: int = 10) -> None:
    try:
        rows = list(client.query(f"SELECT * FROM `{FULL_TABLE_ID}` LIMIT {limit}").result(timeout=60))
    except exceptions.NotFound:
        print("Tabela de batch ainda não existe.")
        return
    except exceptions.Forbidden as e:
        print(f"SELECT bloqueado: {e}")
        return
    for row in rows:
        print(dict(row))


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    batch_load(client)
    show_rows(client)


if __name__ == "__main__":
    main()
