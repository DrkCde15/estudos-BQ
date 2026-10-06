"""Aula 08 — Carga particionada + exemplo GCS (batch, sandbox OK).

Objetivo: particionar no BigQuery e provar a poda com dry run.
- Tabela particionada por DATE `dia`: DDL permitido no sandbox.
- Carga batch com WRITE_TRUNCATE = idempotente.
- WHERE no campo de partição poda bytes (dry run mostra a diferença).
- GCS (load_table_from_uri) fica atrás de BQ_GCS_URI: sem bucket, pula com aviso.

Equivalentes bq CLI:
  bq mk --table --time_partitioning_field=dia --project_id=engdta engdta:staging.aula08_part id:INTEGER,dia:DATE,valor:FLOAT
  bq query --dry_run --project_id=engdta 'SELECT * FROM `engdta.staging.aula08_part` WHERE dia = CURRENT_DATE()'
  bq load --source_format=PARQUET --project_id=engdta engdta:staging.aula08_gcs 'gs://SEU_BUCKET/dados/*.parquet'
"""

import os
from datetime import date, timedelta

from google.api_core import exceptions
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT", "engdta")
DATASET_ID = "staging"
PART_TABLE = f"{PROJECT_ID}.{DATASET_ID}.aula08_part"
GCS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.aula08_gcs"
GCS_URI = os.getenv("BQ_GCS_URI", "")  # ex.: gs://meu-bucket/dados/*.parquet

# Datas relativas a hoje: partições antigas expiram (o dataset usa expiração
# de partição ~60 dias), então datas fixas de 2026-01 sumiriam na carga.
_TODAY = date.today()
DATES = [str(_TODAY - timedelta(days=d)) for d in (2, 1, 0)]
ROWS = [
    {"id": 1, "dia": DATES[0], "valor": 10.5},
    {"id": 2, "dia": DATES[1], "valor": 20.0},
    {"id": 3, "dia": DATES[2], "valor": 30.25},
]

SCHEMA = [
    bigquery.SchemaField("id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("dia", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("valor", "FLOAT64", mode="NULLABLE"),
]


def ensure_partitioned_table(client: bigquery.Client) -> None:
    table = bigquery.Table(PART_TABLE, schema=SCHEMA)
    table.time_partitioning = bigquery.TimePartitioning(field="dia")
    try:
        client.create_table(table, exists_ok=True)
        print(f"Tabela particionada {PART_TABLE}: garantida (partição por dia).")
    except exceptions.Forbidden as e:
        print(f"CREATE particionada bloqueado: {e}")
    except exceptions.BadRequest as e:
        print(f"CREATE particionada recusado: {e}")


def batch_load(client: bigquery.Client) -> None:
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        time_partitioning=bigquery.TimePartitioning(field="dia"),
    )
    try:
        job = client.load_table_from_json(ROWS, PART_TABLE, job_config=job_config)
        job.result(timeout=120)
        t = client.get_table(PART_TABLE)
        print(f"LOAD particionado: {t.num_rows} linha(s) (TRUNCATE).")
    except exceptions.Forbidden as e:
        print(f"LOAD particionado pulado: {e}")


def pruning_demo(client: bigquery.Client) -> None:
    full_scan = f"SELECT * FROM `{PART_TABLE}`"
    pruned = f"SELECT * FROM `{PART_TABLE}` WHERE dia = DATE '{DATES[1]}'"
    for label, sql in (("sem filtro", full_scan), ("com filtro de partição", pruned)):
        try:
            job = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
            print(f"Dry run {label}: ~{job.total_bytes_processed} bytes")
        except exceptions.Forbidden as e:
            print(f"Dry run {label} bloqueado: {e}")
            return


def gcs_demo(client: bigquery.Client) -> None:
    if not GCS_URI:
        print("GCS pulado: defina BQ_GCS_URI=gs://bucket/caminho/*.parquet para testar.")
        print("Ex.: bq load --source_format=PARQUET "
              f"--project_id={PROJECT_ID} {GCS_TABLE} 'gs://BUCKET/dados/*.parquet'")
        return
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.PARQUET,
    )
    try:
        job = client.load_table_from_uri(GCS_URI, GCS_TABLE, job_config=job_config)
        job.result(timeout=300)
        print(f"LOAD GCS OK: {GCS_URI} -> {GCS_TABLE}")
    except (exceptions.Forbidden, exceptions.NotFound, exceptions.BadRequest) as e:
        print(f"LOAD GCS falhou/pulado: {e}")


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    client.create_dataset(bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}"), exists_ok=True)
    ensure_partitioned_table(client)
    batch_load(client)
    pruning_demo(client)
    gcs_demo(client)


if __name__ == "__main__":
    main()
