# Estudos BigQuery

Projeto: `engdta`

## Aula 01 — `aula01.py`: dataset, tabela e labels

Cria (idempotente, `exists_ok=True`):
- Dataset `staging` (equiv. `bq mk --dataset`)
- Tabela `AZURE` vazia, sem schema (equiv. `bq mk --table`)

Fluxo de labels:
1. `set`: `table.labels = {...}` + `update_table(["labels"])`
2. `append`: merge `dict(table.labels or {})` + `update()` — `update_table` faz merge, não replace
3. `delete um`: `table.labels = {"year": None}` — `pop()` ou `{}` **não** apagam
4. `delete todos`: `{k: None for k in table.labels}`

Deletes destrutivos (comentados no código):
```python
client.delete_table(table_ref, not_found_ok=True)
client.delete_dataset(dataset_ref, delete_contents=True, not_found_ok=True)
```

Validação:
```bash
python3 aula01.py
bq show --project_id=engdta staging.AZURE
```