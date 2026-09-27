from google.cloud import bigquery

client = bigquery.Client(project="engdta")

# Referências para o dataset e tabela
dataset_ref = bigquery.DatasetReference(client.project, "staging")
table_ref = bigquery.TableReference(dataset_ref, "AZURE")

# cria o dataset se não existir
dataset = bigquery.Dataset(dataset_ref)
client.create_dataset(dataset, exists_ok=True)

# cria a tabela se não existir
table = bigquery.Table(table_ref)
client.create_table(table, exists_ok=True)

# 1. Set inicial (sobrescreve)
labels = {
    'type': 'social_media',
    'category': 'cloud_computing'
}
azure_table = client.get_table(table_ref)
azure_table.labels = labels
azure_table = client.update_table(azure_table, ["labels"])
print("labels após set:", azure_table.labels)

# 2. Append/update (merge, não sobrescreve)
new_labels = {
    'types': 'software',
    'year': '2023'
}
table = client.get_table(table_ref)
merged = dict(table.labels or {})
merged.update(new_labels)
table.labels = merged
table = client.update_table(table, ["labels"])
print("labels após append:", table.labels)

# 3. Delete um label específico (no BigQuery: valor None deleta)
table = client.get_table(table_ref)
table.labels = {"year": None}
table = client.update_table(table, ["labels"])
print("labels após delete 'year':", table.labels)

# 4. Delete todos os labels (opcional; {} não funciona, tem que ser None por chave)
table = client.get_table(table_ref)
table.labels = {k: None for k in (table.labels or {})}
table = client.update_table(table, ["labels"])

# 5. Delete tabela / dataset (opcional, destrutivo)
client.delete_table(table_ref, not_found_ok=True)
client.delete_dataset(dataset_ref, delete_contents=True, not_found_ok=True)

