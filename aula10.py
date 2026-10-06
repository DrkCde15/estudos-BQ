"""Aula 10 — Poda na prática: dry run comparando filtros (read-only, sandbox OK).

Objetivo: provar com bytes que filtro certo barateia a query.
- Sem filtro: scan cheio.
- WHERE dia = ... (partição): poda física, cai para ~1/N partições.
- WHERE dia + regiao (partição + cluster): poda máxima.
- WHERE valor > ... (sem relação com partição/cluster): NÃO poda, scan cheio.
Tudo via dry_run: estimativa grátis, sem consumir cota.

Equivalente bq CLI:
  bq query --dry_run --project_id=engdta 'SELECT * FROM `engdta.staging.aula09_cluster` WHERE dia = CURRENT_DATE()'
"""

import os

from google.api_core import exceptions
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT", "engdta")
TABLE = f"{PROJECT_ID}.staging.aula09_cluster"

QUERIES = {
    "sem filtro (scan cheio)": f"SELECT * FROM `{TABLE}`",
    "filtro partição": f"SELECT * FROM `{TABLE}` WHERE dia = CURRENT_DATE()",
    "partição + cluster": f"SELECT * FROM `{TABLE}` WHERE dia = CURRENT_DATE() AND regiao = 'sul'",
    "filtro fora do cluster": f"SELECT * FROM `{TABLE}` WHERE valor > 50",
}


def compare(client: bigquery.Client) -> None:
    results: dict[str, int] = {}
    for label, sql in QUERIES.items():
        try:
            job = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
            results[label] = job.total_bytes_processed
            print(f"{label}: ~{job.total_bytes_processed} bytes")
        except (exceptions.Forbidden, exceptions.NotFound) as e:
            print(f"{label}: pulado ({e})")
            return
    full = results.get("sem filtro (scan cheio)", 0)
    if full:
        for label, b in results.items():
            print(f"  {label}: {b / full:.0%} do scan cheio")


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    compare(client)


if __name__ == "__main__":
    main()
