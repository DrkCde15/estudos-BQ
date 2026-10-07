-- Aula 03 (SQL) — Agregados por UF em `engdta.aula_bq.srag_2026`.

-- 1. Casos por UF notificante, do maior para o menor.
SELECT SG_UF_NOT AS uf, COUNT(*) AS casos
FROM `engdta.aula_bq.srag_2026`
GROUP BY uf
ORDER BY casos DESC;

-- 2. UF notificante vs UF de residência: divergem? (migração/busca de atendimento)
SELECT SG_UF_NOT AS uf_notific,
       SG_UF AS uf_residencia,
       COUNT(*) AS casos
FROM `engdta.aula_bq.srag_2026`
WHERE SG_UF_NOT != SG_UF
GROUP BY uf_notific, uf_residencia
ORDER BY casos DESC
LIMIT 20;

-- 3. Peso relativo: % de cada UF no total (janela sobre o agregado).
SELECT SG_UF_NOT AS uf,
       COUNT(*) AS casos,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_total
FROM `engdta.aula_bq.srag_2026`
GROUP BY uf
ORDER BY casos DESC;
