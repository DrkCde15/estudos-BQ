"""Aula 04 — DDL: CREATE TABLE IF NOT EXISTS + CREATE OR REPLACE VIEW.

Objetivo: versionar estrutura via DDL (permitido no sandbox), sem DML.
- CREATE TABLE IF NOT EXISTS é idempotente (re-run não erra).
- CREATE OR REPLACE VIEW sempre converge para a definição do código.
- Tipos: BQ exige NULLABLE/REPEATED em ALTER (aula02); em CREATE pode usar REQUIRED.

Equivalentes bq CLI:
  bq mk --table --project_id=engdta engdta:staging.aula04_demo id:INTEGER,nome:STRING,created_at:TIMESTAMP
  bq query --project_id=engdta 'CREATE OR REPLACE VIEW `engdta.staging.v_biq_copy` AS SELECT keep_me FROM `engdta.staging.biq_copy`'
"""

import os

from google.api_core import exceptions
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT", "engdta")
DATASET_ID = "staging"
DEMO_TABLE = f"{PROJECT_ID}.{DATASET_ID}.aula04_demo"
VIEW_ID = f"{PROJECT_ID}.{DATASET_ID}.v_biq_copy"
SOURCE_TABLE = f"{PROJECT_ID}.{DATASET_ID}.biq_copy"


def ensure_demo_table(client: bigquery.Client) -> None:
    sql = f"""CREATE TABLE IF NOT EXISTS `{DEMO_TABLE}` (
      id INT64 NOT NULL,
      nome STRING,
      created_at TIMESTAMP
    )"""
    try:
        client.query(sql).result(timeout=60)
        print(f"Tabela {DEMO_TABLE}: garantida (IF NOT EXISTS).")
    except exceptions.Forbidden as e:
        print(f"CREATE TABLE bloqueado: {e}")
    except exceptions.BadRequest as e:
        print(f"CREATE TABLE recusado: {e}")


def ensure_view(client: bigquery.Client) -> None:
    sql = f"""CREATE OR REPLACE VIEW `{VIEW_ID}` AS
      SELECT keep_me FROM `{SOURCE_TABLE}`"""
    try:
        client.query(sql).result(timeout=60)
        print(f"View {VIEW_ID}: convergida (OR REPLACE).")
    except exceptions.NotFound as e:
        print(f"View pulada — tabela fonte ainda não existe: {e}")
    except (exceptions.Forbidden, exceptions.BadRequest) as e:
        print(f"View pulada: {e}")


def describe_demo(client: bigquery.Client) -> None:
    try:
        table = client.get_table(DEMO_TABLE)
        print(f"Schema {DEMO_TABLE}: {[(f.name, f.field_type, f.mode) for f in table.schema]}")
    except exceptions.NotFound:
        print(f"Tabela {DEMO_TABLE} não encontrada.")


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    ensure_demo_table(client)
    ensure_view(client)
    describe_demo(client)


if __name__ == "__main__":
    main()
