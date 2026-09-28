"""Aula 06 — Introspecção e custo: catálogo + INFORMATION_SCHEMA + dry run.

Objetivo: responder "o que existe e quanto custa consultar?" só com leitura.
Tudo aqui é read-only e funciona no sandbox.
- client.list_datasets / list_tables: inventário.
- get_table: num_rows, num_bytes (custo de scan cheio).
- INFORMATION_SCHEMA.TABLES/COLUMNS: linhagem básica e schema.
- dry_run: estimativa antes de qualquer SELECT pesado (ver aula03).

Equivalentes bq CLI:
  bq ls --project_id=engdta
  bq ls --project_id=engdta engdta:staging
  bq show --project_id=engdta engdta:staging.biq_copy
  bq query --project_id=engdta 'SELECT table_name, row_count FROM `engdta.staging.INFORMATION_SCHEMA.TABLES`'
"""

import os

from google.api_core import exceptions
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT", "engdta")
DATASET_ID = "staging"


def inventory(client: bigquery.Client) -> None:
    print(f"== datasets de {PROJECT_ID} ==")
    for ds in client.list_datasets():
        print(f"- {ds.dataset_id}")
    print(f"\n== tabelas de {DATASET_ID} ==")
    try:
        for t in client.list_tables(f"{PROJECT_ID}.{DATASET_ID}"):
            print(f"- {t.table_id} ({t.table_type})")
    except exceptions.NotFound:
        print(f"Dataset {DATASET_ID} não existe.")


def table_stats(client: bigquery.Client, table_id: str) -> None:
    full = f"{PROJECT_ID}.{DATASET_ID}.{table_id}"
    try:
        t = client.get_table(full)
    except exceptions.NotFound:
        print(f"{full}: não encontrada.")
        return
    gb = (t.num_bytes or 0) / 1e9
    print(f"{full}: {t.num_rows} linhas, ~{gb:.4f} GB (scan cheio ≈ esse volume).")


def info_schema(client: bigquery.Client) -> None:
    sql = f"""SELECT table_name, table_type
      FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.TABLES`
      ORDER BY table_name"""
    try:
        rows = list(client.query(sql).result(timeout=60))
    except exceptions.Forbidden as e:
        print(f"INFORMATION_SCHEMA bloqueado: {e}")
        return
    print("INFORMATION_SCHEMA.TABLES:")
    for r in rows:
        print(f"- {r.table_name} ({r.table_type})")


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    inventory(client)
    for tid in ("biq_copy", "aula04_demo", "aula05_batch"):
        table_stats(client, tid)
    info_schema(client)


if __name__ == "__main__":
    main()
