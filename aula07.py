"""Aula 07 — Upload de arquivos locais: CSV, JSON e Parquet (batch, sandbox OK).

Objetivo: enviar arquivo de verdade via load job (permitido sem billing),
ao contrário do streaming (403, ver aula02/05).
- Arquivos em data/: clientes.csv, clientes.json (NDJSON), clientes.parquet.
- load_table_from_file + WRITE_TRUNCATE = idempotente (re-run substitui).
- Schema explícito vence autodetect: tipos estáveis, sem surpresa (ex.: id vira STRING).
- Parquet preserva tipos; CSV precisa de skip_leading_rows + tipos declarados.

Equivalentes bq CLI:
  bq load --source_format=CSV --skip_leading_rows=1 --project_id=engdta engdta:staging.aula07_csv ./data/clientes.csv id:INTEGER,nome:STRING,ativo:BOOLEAN
  bq load --source_format=NEWLINE_DELIMITED_JSON --project_id=engdta engdta:staging.aula07_json ./data/clientes.json
  bq load --source_format=PARQUET --project_id=engdta engdta:staging.aula07_parquet ./data/clientes.parquet
"""

import os
from pathlib import Path

from google.api_core import exceptions
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT", "engdta")
DATASET_ID = "staging"
DATA_DIR = Path(__file__).resolve().parent / "data"

SCHEMA = [
    bigquery.SchemaField("id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("nome", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("ativo", "BOOL", mode="NULLABLE"),
]

FILES = [
    # (arquivo, tabela, formato, kwargs extras)
    ("clientes.csv", "aula07_csv", bigquery.SourceFormat.CSV, {"skip_leading_rows": 1}),
    ("clientes.json", "aula07_json", bigquery.SourceFormat.NEWLINE_DELIMITED_JSON, {}),
    ("clientes.parquet", "aula07_parquet", bigquery.SourceFormat.PARQUET, {}),
]


def load_file(client: bigquery.Client, filename: str, table: str, source_format: str, **kwargs) -> None:
    path = DATA_DIR / filename
    if not path.exists():
        print(f"{filename}: arquivo não encontrado em {path}, pulado.")
        return
    full = f"{PROJECT_ID}.{DATASET_ID}.{table}"
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=source_format,
        **kwargs,
    )
    try:
        with open(path, "rb") as f:
            job = client.load_table_from_file(f, full, job_config=job_config)
            job.result(timeout=120)
    except exceptions.Forbidden as e:
        print(f"LOAD {table} pulado (sandbox/billing): {e}")
        return
    t = client.get_table(full)
    print(f"LOAD {table} <- {filename}: {t.num_rows} linha(s) via {source_format} (TRUNCATE).")


def autodetect_demo(client: bigquery.Client) -> None:
    """Mostra por que explícito > autodetect: compara o schema inferido do CSV real."""
    path = DATA_DIR / "clientes.csv"
    full = f"{PROJECT_ID}.{DATASET_ID}.aula07_autodetect"
    job_config = bigquery.LoadJobConfig(
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
    )
    try:
        with open(path, "rb") as f:
            job = client.load_table_from_file(f, full, job_config=job_config)
            job.result(timeout=120)
        t = client.get_table(full)
        print(f"Autodetect inferiu: {[(f.name, f.field_type, f.mode) for f in t.schema]}")
        print("Lição: autodetect pode inferir tipos instáveis; prefira schema explícito.")
    except exceptions.Forbidden as e:
        print(f"Autodetect demo pulada: {e}")


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    client.create_dataset(bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}"), exists_ok=True)
    for filename, table, fmt, kwargs in FILES:
        load_file(client, filename, table, fmt, **kwargs)
    autodetect_demo(client)


if __name__ == "__main__":
    main()
