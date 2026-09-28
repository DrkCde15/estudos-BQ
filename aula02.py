import os

from google.api_core import exceptions
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT", "engdta")
DATASET_ID = "staging"
TABLE_ID = "biq_copy"
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

COLUMNS_TO_ENSURE = [
    bigquery.SchemaField("saved2", "BOOLEAN", mode="NULLABLE"),
    bigquery.SchemaField("permlink2", "STRING", mode="NULLABLE"),
    # Âncora: o BigQuery não permite dropar a última coluna da tabela (400).
    # Sem ela, dropar saved2+permlink2 de uma tabela só com essas 2 falha.
    bigquery.SchemaField("keep_me", "STRING", mode="NULLABLE"),
]


def ensure_dataset(client: bigquery.Client, dataset_ref) -> None:
    # cria o dataset se não existir (idempotente)
    client.create_dataset(bigquery.Dataset(dataset_ref), exists_ok=True)


def ensure_table(client: bigquery.Client, table_ref) -> None:
    # cria a tabela se não existir (idempotente, sem schema inicial)
    client.create_table(bigquery.Table(table_ref), exists_ok=True)


def ensure_columns(client: bigquery.Client, table_ref) -> None:
    # Adiciona colunas só se ainda não existirem (idempotente).
    # Reexecutar sem essa checagem falharia com "Duplicate column name".
    bq_table = client.get_table(table_ref)
    existing = {field.name for field in bq_table.schema}
    missing = [f for f in COLUMNS_TO_ENSURE if f.name not in existing]
    if not missing:
        print("Colunas já existem, nada a alterar.")
        return
    bq_table.schema = list(bq_table.schema) + missing
    client.update_table(bq_table, ["schema"])
    print(f"Colunas adicionadas: {[f.name for f in missing]}")


def insert_sample_rows(client: bigquery.Client, table_ref) -> None:
    rows_to_insert = [
        {"saved2": True, "permlink2": "https://example.com/post1"},
        {"saved2": False, "permlink2": "https://example.com/post2"},
    ]
    # Evita duplicar a cada reexecução: insere só o que ainda não está lá.
    # Usa DML via query job em vez de insert_rows_json (streaming insertAll),
    # porque o streaming é bloqueado no sandbox (403). Se o projeto também
    # bloqueia DML sem billing, o insert é pulado sem abortar a aula (DDL).
    try:
        existing_links = {
            row.permlink2
            for row in client.query(
                f"SELECT permlink2 FROM `{FULL_TABLE_ID}`"
            ).result(timeout=60)
        }
    except exceptions.Forbidden as e:
        print("SELECT pulado: projeto sem billing (sandbox).")
        print(f"Detalhe: {e}")
        return
    new_rows = [r for r in rows_to_insert if r["permlink2"] not in existing_links]
    if not new_rows:
        print("Linhas de exemplo já existem, nada a inserir.")
        return
    values_clause = ", ".join(
        f"(@saved{i}, @link{i})" for i in range(len(new_rows))
    )
    params: list[bigquery.ScalarQueryParameter] = []
    for i, r in enumerate(new_rows):
        params.append(bigquery.ScalarQueryParameter(f"saved{i}", "BOOL", r["saved2"]))
        params.append(bigquery.ScalarQueryParameter(f"link{i}", "STRING", r["permlink2"]))
    try:
        job = client.query(
            f"INSERT INTO `{FULL_TABLE_ID}` (saved2, permlink2) VALUES {values_clause}",
            job_config=bigquery.QueryJobConfig(query_parameters=params),
        )
        job.result(timeout=120)
    except exceptions.Forbidden as e:
        print("INSERT pulado: DML exige billing ativo; sandbox bloqueia (403 billingNotEnabled).")
        print("Ative billing em https://console.cloud.google.com/billing para praticar DML/inserts.")
        print(f"Detalhe: {e}")
        return
    print(f"{len(new_rows)} linha(s) inserida(s) via DML.")


def drop_columns(client: bigquery.Client, columns: list[str]) -> None:
    # IF EXISTS já é idempotente. Um ALTER por coluna (sintaxe mais segura).
    # query().result() já bloqueia até DONE — sem polling manual com sleep/reload.
    for column in columns:
        try:
            job = client.query(
                f"ALTER TABLE `{FULL_TABLE_ID}` DROP COLUMN IF EXISTS {column}"
            )
            job.result(timeout=120)
        except exceptions.BadRequest as e:
            # Ex.: tentar dropar a última coluna restante (400).
            print(f"DROP de {column} recusado pelo BigQuery: {e}")
            print("Dica: mantenha ao menos 1 coluna (aqui: keep_me) ou delete a tabela.")
            continue
        print(f"Coluna {column}: removida (ou já inexistente).")


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    dataset_ref = bigquery.DatasetReference(client.project, DATASET_ID)
    table_ref = bigquery.TableReference(dataset_ref, TABLE_ID)

    ensure_dataset(client, dataset_ref)
    ensure_table(client, table_ref)
    ensure_columns(client, table_ref)
    insert_sample_rows(client, table_ref)
    drop_columns(client, ["saved2", "permlink2"])


if __name__ == "__main__":
    main()