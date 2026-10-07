# Estudos BigQuery (SQL)

Alvo: `engdta.aula_bq` (projeto `engdta`, dataset `aula_bq`, location `US`).

Como rodar cada aula:
```bash
bq query --project_id=engdta --use_legacy_sql=false < aula01.sql
# só validar a sintaxe, sem executar:
bq query --dry_run --project_id=engdta --use_legacy_sql=false < aula01.sql
```

Pré-requisitos:
```bash
gcloud auth list  # conta ativa
bq ls --project_id=engdta  # deve listar aula_bq
```

## Dados: `srag_2026` (SRAG/SIVEP-Gripe 2026)

- 10.000 linhas, ~7,5 MB, sem particionamento/clustering, expira em 06/dez.
- Colunas-chave: `DT_NOTIFIC`, `DT_SIN_PRI` (timestamps), `SG_UF_NOT`, `SG_UF`, `CS_SEXO`, `NU_IDADE_N`, `SEM_NOT`, `SEM_PRI`.
- Scan cheio ≈ 7,5 MB — queries de estudo custam centavos de cota, mas use `dry_run` e `LIMIT` por hábito.

## Aula 01 — `aula01.sql`: primeira leitura

```sql
SELECT *
FROM `engdta.aula_bq.srag_2026`
LIMIT 30;
```

Objetivo: confirmar acesso, ver o shape real (tipos, nulos, valores). `LIMIT 30` lê a tabela toda no scan (7,5 MB) — barato aqui, proibitivo em tabelas grandes; nas próximas aulas, selecionamos só as colunas necessárias.

Labels/metadados (não têm DDL em SQL — via CLI):
```bash
bq update --set_label fonte:sivep_gripe --set_label ano:2026 --project_id=engdta engdta:aula_bq.srag_2026
bq show --project_id=engdta aula_bq.srag_2026
```

## Arquivos `data/` ↔ tabelas (fontes versionadas)

| Arquivo | Tabela | Linhas | Tamanho | Obs |
|---|---|---|---|---|
| `data/brasil_estados.csv` | `brasil_estados` | 30.842 | ~5,4 MB | COVID por município/dia (`epi_week, date, state, city, newCases, deaths...`), vírgula |
| `data/brasil_total.csv` | `brasil_total` | 28 | ~6 KB | Consolidado por UF (2023-03-18), vírgula |
| `data/srag_2026_amostra10k.csv` | `srag_2026` | 10.000 | ~8 MB | Amostra SIVEP-Gripe, **separador `;`** |

Recarregar do zero (batch, idempotente com `WRITE_TRUNCATE`):
```bash
bq load --source_format=CSV --skip_leading_rows=1 --autodetect --project_id=engdta engdta:aula_bq.brasil_total ./data/brasil_total.csv
bq load --source_format=CSV --skip_leading_rows=1 --field_delimiter=';' --autodetect --project_id=engdta engdta:aula_bq.srag_2026 ./data/srag_2026_amostra10k.csv
```
Nota: ~13,5 MB em CSV no git é aceitável; se os arquivos crescerem, mova para GCS (`load_table_from_uri`) em vez de versionar.

## Roadmap (aulas em `.sql` sobre `engdta.aula_bq`)

- **02 ✅ `aula02.sql` — Perfil das colunas:** cardinalidade, tops, nulos (`COUNTIF`), faixa de idades.
- **03 ✅ `aula03.sql` — Agregados por UF:** casos por `SG_UF_NOT`, divergência notificação×residência, % do total (window).
- **04 ✅ `aula04.sql` — Tempo:** casos por `SEM_NOT`, por mês (`DATE_TRUNC`), coerência semana×mês.
- **05 — Idade/sexo:** faixas de `NU_IDADE_N` com `CASE`, cruzado com `CS_SEXO`.
- **06 — Qualidade:** nulos por coluna (`COUNTIF(x IS NULL)`), datas futuras, idades impossíveis.
- **07 — Filtros que podam:** `SELECT` só de colunas necessárias + `dry_run` comparando `SELECT *` vs lista explícita.
- **08 — Views:** `CREATE OR REPLACE VIEW aula_bq.v_srag_resumo` com o agregado da aula 03.
- **09 — Tabela derivada particionada:** `CREATE TABLE aula_bq.srag_por_dia PARTITION BY dia AS SELECT ...` + `dry_run` com/sem filtro de partição.
- **10 — Clustering:** `CLUSTER BY SG_UF_NOT` na derivada + comparativo de bytes.
- **11 — Auditoria de custo:** `INFORMATION_SCHEMA.JOBS` — bytes por query rodada no projeto.
- **12 — Qualidade avançada:** duplicadas por `NU_NOTIFIC` (`GROUP BY ... HAVING COUNT(*) > 1`), quarentena em tabela à parte.
- **13–16 — Janelas e coortes:** `ROW_NUMBER`, `LAG` (intervalo notificação→sintomas), coorte semanal.
- **17–20 — Disponibilização (Evidence):** conexão `BigQuery`/`us` já salva; sources versionadas em `sources/`, ex.: `select SG_UF_NOT, count(*) n from engdta.aula_bq.srag_2026 group by 1`.
- **21–30 — Projeto final:** dicionário de dados, pipeline `aula_bq` → views/marts, runbook e checklist de produção.

Regras: todo `.sql` roda com `bq query < aulaNN.sql`; DML (`INSERT`/`MERGE`) só com billing ativo (sandbox retorna 403 — ver histórico do projeto); `dry_run` antes de qualquer scan novo.

## Notas de ambiente

- O dataset antigo `staging` (aulas `.py`) não existe mais; o curso recomeçou em `aula_bq` com dados reais.
- Conexão BI (Evidence): `BigQuery`/`SERVICE_ACCOUNT`/`us`, chave em `~/evidence-bq-key.json` (fora do repo, `chmod 600`).
