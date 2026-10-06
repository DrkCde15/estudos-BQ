"""Aula 11 — Plano de execução: ler os stages do job (sandbox OK).

Objetivo: sair do "rodou" para o "como rodou".
- Todo query job concluído expõe job.query_plan: stages com o que cada
  etapa leu/escreveu/embaralhou (shuffle).
- Sinais de alerta: stage com shuffle muito maior que input (join sem chave
  seletiva), STAGE de scan lendo a tabela inteira (faltou poda, ver aula10).
- Query jobs SELECT funcionam no sandbox; o plano vem de graça após result().

Equivalente bq CLI (mostra timeline/resumo, não os stages detalhados):
  bq query --project_id=engdta 'SELECT regiao, SUM(valor) FROM `engdta.staging.aula09_cluster` GROUP BY regiao'
"""

import os

from google.api_core import exceptions
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT", "engdta")
TABLE = f"{PROJECT_ID}.staging.aula09_cluster"

SQL = f"""SELECT regiao, COUNT(*) AS n, SUM(valor) AS total
  FROM `{TABLE}` GROUP BY regiao ORDER BY regiao"""


def show_plan(client: bigquery.Client) -> None:
    # use_query_cache=False: sem isso, o 2º run vem do cache (0 bytes, sem plano).
    try:
        job = client.query(SQL, job_config=bigquery.QueryJobConfig(use_query_cache=False))
        rows = list(job.result(timeout=120))
    except (exceptions.Forbidden, exceptions.NotFound, exceptions.BadRequest) as e:
        print(f"Query pulada: {e}")
        return
    print("Resultado:")
    for r in rows:
        print(f"  {r.regiao}: n={r.n} total={r.total}")
    print(f"\nJob {job.job_id}: {job.total_bytes_processed} bytes processados")
    print("Stages:")
    for stage in job.query_plan or []:
        kinds = ", ".join(s.kind for s in (stage.steps or [])[:4])
        print(
            f"  - {stage.name}: in={stage.records_read} rec / "
            f"out={stage.records_written} rec, shuffle={stage.shuffle_output_bytes} bytes"
            + (f" [{kinds}]" if kinds else "")
        )
    if not job.query_plan:
        print("  (plano indisponível para este job)")


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    show_plan(client)


if __name__ == "__main__":
    main()
