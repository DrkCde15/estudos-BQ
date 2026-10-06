"""Aula 09 — Particionamento + clustering via DDL (sandbox OK).

Objetivo: a combinação que mais economiza scan no BigQuery.
- PARTITION BY dia: poda física (partições ignoradas nem são lidas).
- CLUSTER BY regiao: ordena dentro da partição; filtro na coluna clusterizada
  lê só os blocos relevantes (poda aproximada, não garantida como partição).
- Regra: particione pela coluna de filtro mais comum (geralmente data),
  clustere por até 4 colunas de filtro/agrupamento (alta cardinalidade OK).
- Datas relativas a hoje: partições antigas expiram ~60d no dataset (ver aula08).

Equivalentes bq CLI:
  bq mk --table --time_partitioning_field=dia --clustering_fields=regiao --project_id=engdta engdta:staging.aula09_cluster id:INTEGER,dia:DATE,regiao:STRING,valor:FLOAT
  bq show --project_id=engdta engdta:staging.aula09_cluster
"""

import os
from datetime import date, timedelta

from google.api_core import exceptions
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT", "engdta")
DATASET_ID = "staging"
TABLE = f"{PROJECT_ID}.{DATASET_ID}.aula09_cluster"

_TODAY = date.today()
DATES = [str(_TODAY - timedelta(days=d)) for d in (2, 1, 0)]
REGIOES = ["sul", "sudeste", "norte"]
ROWS = [
    {"id": i, "dia": DATES[i % 3], "regiao": REGIOES[i % 3], "valor": float(i * 10)}
    for i in range(1, 10)
]

SCHEMA = [
    bigquery.SchemaField("id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("dia", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("regiao", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("valor", "FLOAT64", mode="NULLABLE"),
]


def ensure_table(client: bigquery.Client) -> None:
    sql = f"""CREATE TABLE IF NOT EXISTS `{TABLE}` (
      id INT64 NOT NULL, dia DATE NOT NULL, regiao STRING, valor FLOAT64
    ) PARTITION BY dia CLUSTER BY regiao"""
    try:
        client.query(sql).result(timeout=60)
        print(f"Tabela {TABLE}: garantida (PARTITION BY dia, CLUSTER BY regiao).")
    except (exceptions.Forbidden, exceptions.BadRequest) as e:
        print(f"CREATE bloqueado/recusado: {e}")


def batch_load(client: bigquery.Client) -> None:
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    try:
        job = client.load_table_from_json(ROWS, TABLE, job_config=job_config)
        job.result(timeout=120)
        print(f"LOAD: {client.get_table(TABLE).num_rows} linha(s) (TRUNCATE).")
    except exceptions.Forbidden as e:
        print(f"LOAD pulado: {e}")


def describe(client: bigquery.Client) -> None:
    try:
        t = client.get_table(TABLE)
        print(f"Partição: {t.time_partitioning}, cluster: {t.clustering_fields}")
    except exceptions.NotFound:
        print("Tabela ainda não existe.")


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    client.create_dataset(bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}"), exists_ok=True)
    ensure_table(client)
    batch_load(client)
    describe(client)


if __name__ == "__main__":
    main()
