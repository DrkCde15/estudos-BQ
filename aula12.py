"""Aula 12 — Views materializadas: conceito + tentativa sandbox-first.

Objetivo: saber quando a MV paga a conta (e quando não).
- View lógica (aula04): zero storage, custo toda vez que consulta.
- MV: armazena o agregado, BigQuery reescreve queries para ler a MV
  (smart tuning) e cobra só o refresh incremental.
- Regra prática: MV vale para agregado pesado consultado com frequência e
  com tolerância a atraso de refresh; para dado pequeno ou consulta rara,
  a view lógica + poda (aulas 09–10) já basta.
- Testado no sandbox: o CREATE da MV funciona; o refresh automático pode
  exigir billing (ver `mview_last_refresh_time`). O código garante também a
  view lógica equivalente como fallback e compara o custo via dry run.

Equivalentes bq CLI:
  bq query --project_id=engdta 'CREATE MATERIALIZED VIEW `engdta.staging.mv_aula09` AS SELECT regiao, SUM(valor) total FROM `engdta.staging.aula09_cluster` GROUP BY regiao'
  bq show --project_id=engdta engdta:staging.mv_aula09
"""

import os

from google.api_core import exceptions
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT", "engdta")
SOURCE = f"{PROJECT_ID}.staging.aula09_cluster"
MV = f"{PROJECT_ID}.staging.mv_aula09"
VIEW = f"{PROJECT_ID}.staging.v_aula09_totais"

AGG_SQL = f"SELECT regiao, COUNT(*) AS n, SUM(valor) AS total FROM `{SOURCE}` GROUP BY regiao"


def try_materialized_view(client: bigquery.Client) -> None:
    try:
        client.query(f"CREATE MATERIALIZED VIEW `{MV}` AS {AGG_SQL}").result(timeout=120)
        print(f"MV {MV}: criada.")
        mv = client.get_table(MV)
        print(f"  refresh: {mv.mview_enable_refresh}, última: {mv.mview_last_refresh_time}")
    except exceptions.Forbidden as e:
        print("MV pulada: exige billing (403 no sandbox). Fallback: view lógica abaixo.")
        print(f"Detalhe: {str(e)[:200]}")
    except exceptions.BadRequest as e:
        print(f"MV recusada (já existe com outra definição? fonte ausente?): {str(e)[:200]}")


def ensure_logic_view(client: bigquery.Client) -> None:
    try:
        client.query(f"CREATE OR REPLACE VIEW `{VIEW}` AS {AGG_SQL}").result(timeout=60)
        print(f"View lógica {VIEW}: garantida como fallback funcional.")
    except (exceptions.Forbidden, exceptions.NotFound) as e:
        print(f"View lógica pulada: {e}")


def compare_cost(client: bigquery.Client) -> None:
    for label, sql in (
        ("base (scan direto)", f"SELECT regiao, SUM(valor) FROM `{SOURCE}` GROUP BY regiao"),
        ("via view lógica", f"SELECT * FROM `{VIEW}`"),
    ):
        try:
            job = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
            print(f"Dry run {label}: ~{job.total_bytes_processed} bytes (view lógica não economiza; MV economizaria)")
        except (exceptions.Forbidden, exceptions.NotFound) as e:
            print(f"Dry run {label} pulado: {e}")
            return


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    try_materialized_view(client)
    ensure_logic_view(client)
    compare_cost(client)


if __name__ == "__main__":
    main()
