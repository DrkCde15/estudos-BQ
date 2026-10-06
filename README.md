# Estudos BigQuery

Projeto: `engdta` (override via `GCP_PROJECT`)

Pré-requisitos:
```bash
.venv/bin/python -c "import google.cloud.bigquery; print('ok')"
gcloud auth list  # conta ativa
# Se o Python reclamar de credenciais (ADC):
gcloud auth application-default login
```

## Aula 01 — `aula01.py`: dataset, tabela e labels

Cria (idempotente, `exists_ok=True`):
- Dataset `staging` (equiv. `bq mk --dataset`)
- Tabela `AZURE` vazia, sem schema (equiv. `bq mk --table`)

Fluxo de labels:
1. `set`: `table.labels = {...}` + `update_table(["labels"])` (substitui)
2. `append`: merge manual `dict(table.labels or {})` + `update()` — o merge é feito no código, não pelo `update_table`
3. `delete um`: `table.labels = {"year": None}` — `pop()` ou `{}` **não** apagam
4. `delete todos`: `{k: None for k in table.labels}`

Atenção — deletes destrutivos **ativos** em `aula01.py:51-52` (não comentados):
```python
client.delete_table(table_ref, not_found_ok=True)
client.delete_dataset(dataset_ref, delete_contents=True, not_found_ok=True)
```
Todo run apaga tabela + dataset ao final. Comente essas linhas se quiser validar depois com `bq show`.

Validação:
```bash
.venv/bin/python aula01.py
bq show --project_id=engdta staging.AZURE
```

## Aula 02 — `aula02.py`: evolução de schema (DDL) idempotente

Alvo: `engdta.staging.biq_copy`. Funções em `aula02.py`:
- `ensure_dataset` / `ensure_table`: criação idempotente (`exists_ok=True`)
- `ensure_columns`: adiciona `saved2:BOOLEAN`, `permlink2:STRING`, `keep_me:STRING` (todas NULLABLE) **só se faltarem** — re-run sem essa checagem falharia com coluna duplicada
- `insert_sample_rows`: DML `INSERT INTO ... VALUES (@saved, @link)` com query parameters, inserindo só `permlink2` novos
- `drop_columns`: `ALTER TABLE ... DROP COLUMN IF EXISTS` (um por coluna); `query().result()` já espera até DONE, sem `sleep`/`reload`

Limites do sandbox (sem billing), já tratados no código:
- `insert_rows_json` (streaming `insertAll`) → `403 Streaming insert is not allowed` — por isso usa DML
- DML sem billing → `403 billingNotEnabled` — o insert é pulado com aviso, sem abortar o DDL
- `DROP COLUMN` da última coluna → `400 Cannot DROP last column` — por isso existe a âncora `keep_me`

Run e validação:
```bash
.venv/bin/python aula02.py
bq show --project_id=engdta --schema staging.biq_copy
bq query --project_id=engdta 'SELECT * FROM `engdta.staging.biq_copy` LIMIT 10'
```

## Módulo 1 (03–06) — Leitura, DDL e carga batch ✅ testado no sandbox

Formato misto: cada aula é um `.py` idempotente que executa SQL via `client.query()` + comenta o equivalente `bq CLI`.

- **Aula 03 — `aula03.py`: query jobs.** `dry_run` para estimar bytes antes de executar, `SELECT * LIMIT`, query parametrizada (`@prefix`). Tudo read-only.
  ```bash
  .venv/bin/python aula03.py
  bq query --dry_run --project_id=engdta 'SELECT * FROM `engdta.staging.biq_copy` LIMIT 10'
  ```
- **Aula 04 — `aula04.py`: DDL.** `CREATE TABLE IF NOT EXISTS staging.aula04_demo` + `CREATE OR REPLACE VIEW staging.v_biq_copy`. Re-run converge, sem erro.
  ```bash
  .venv/bin/python aula04.py
  bq show --project_id=engdta staging.aula04_demo
  ```
- **Aula 05 — `aula05.py`: batch vs streaming.** `load_table_from_json` com `WRITE_TRUNCATE` (batch, permitido no sandbox) vs `insert_rows_json` (streaming, 403). Re-run substitui, não duplica.
  ```bash
  .venv/bin/python aula05.py
  bq show --project_id=engdta staging.aula05_batch
  ```
- **Aula 06 — `aula06.py`: introspecção e custo.** `list_datasets`/`list_tables`, `get_table` (`num_rows`/`num_bytes`), `INFORMATION_SCHEMA.TABLES`, tudo read-only.
  ```bash
  .venv/bin/python aula06.py
  bq ls --project_id=engdta engdta:staging
  ```

## Módulo 2 (07–08) — Envio de arquivos ✅ testado no sandbox

- **Aula 07 — `aula07.py`: upload de arquivos reais.** Arquivos em `data/` (`clientes.csv`, `clientes.json`, `clientes.parquet`, 3 linhas cada) enviados via `load_table_from_file` com `WRITE_TRUNCATE` + schema explícito. Demo `autodetect=True` no CSV real: inferiu `id INTEGER NULLABLE` vs declarado `REQUIRED` (lição: prefira schema declarado).
  ```bash
  .venv/bin/python aula07.py
  bq show --project_id=engdta staging.aula07_csv staging.aula07_json staging.aula07_parquet
  bq load --source_format=CSV --skip_leading_rows=1 --project_id=engdta engdta:staging.aula07_csv ./data/clientes.csv id:INTEGER,nome:STRING,ativo:BOOLEAN
  ```
- **Aula 08 — `aula08.py`: carga particionada + GCS.** Tabela particionada por `dia` (DDL), batch load com datas relativas a hoje (partições antigas expiram ~60d no dataset — datas fixas de janeiro sumiram no teste), `dry_run` provando a poda (72 bytes cheio vs 24 filtrado). GCS via `load_table_from_uri` atrás de `BQ_GCS_URI` (pula com aviso sem bucket).
  ```bash
  .venv/bin/python aula08.py
  BQ_GCS_URI='gs://BUCKET/dados/*.parquet' .venv/bin/python aula08.py
  bq show --project_id=engdta staging.aula08_part
  ```

## Roadmap até a aula 30

- **Módulo 1 (03–06)** ✅ — Leitura, DDL, carga batch, catálogo (feito, testado).
- **Módulo 2 (07–08)** ✅ — Upload de arquivos + particionamento (feito, testado).
## Módulo 3 (09–12) — Clustering, poda, plano e MVs ✅ testado no sandbox

- **Aula 09 — `aula09.py`: particionamento + clustering.** `CREATE TABLE ... PARTITION BY dia CLUSTER BY regiao` + batch load de 9 linhas (datas relativas a hoje, cf. aula08). Re-run converge.
  ```bash
  .venv/bin/python aula09.py
  bq show --project_id=engdta staging.aula09_cluster
  ```
- **Aula 10 — `aula10.py`: poda em números.** `dry_run` × 4 filtros: cheio 279 B, partição 93 B (33%), partição+cluster 93 B, filtro fora do cluster 279 B (100% — não podou).
  ```bash
  .venv/bin/python aula10.py
  ```
- **Aula 11 — `aula11.py`: plano de execução.** `GROUP BY` com `use_query_cache=False` (sem isso o 2º run vem do cache: 0 bytes, sem plano) + leitura dos stages (`READ/AGGREGATE/WRITE`, `READ/SORT/WRITE`, shuffle por stage).
  ```bash
  .venv/bin/python aula11.py
  ```
- **Aula 12 — `aula12.py`: materialized view.** `CREATE MATERIALIZED VIEW` funcionou no sandbox (refresh automático pode exigir billing); fallback `v_aula09_totais` + `dry_run` mostrando que view lógica não economiza scan.
  ```bash
  .venv/bin/python aula12.py
  bq show --project_id=engdta staging.mv_aula09
  ```

## Roadmap até a aula 30

- **Módulo 1 (03–06)** ✅ — Leitura, DDL, carga batch, catálogo (feito, testado).
- **Módulo 2 (07–08)** ✅ — Upload de arquivos + particionamento (feito, testado).
- **Módulo 3 (09–12)** ✅ — Clustering, poda, plano de execução, MVs (feito, testado).
- **Módulo 4 (13–16)** — Qualidade: `NOT NULL`/`UNIQUE` (limites do BQ), checagens `COUNTIF`, `MERGE` idempotente (pula sem billing), quarentena de inválidas.
- **Módulo 5 (17–20)** — Rotinas e agendamento: `CREATE PROCEDURE`/`SCHEDULED QUERY`, data lógica, backfill por janela.
- **Módulo 6 (21–24)** — Custos e segurança: `INFORMATION_SCHEMA.JOBS`, labels por job, IAM por dataset, máscara de PII, regionamento.
- **Módulo 7 (25–30)** — Projeto final: pipeline staging→marts só com DDL+batch+views, dicionário, runbook e checklist de produção.

Regra de todas as aulas: idempotente + sandbox-first (pula com aviso o que exigir billing).