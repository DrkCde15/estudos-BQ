-- Aula 04 (SQL) — Tempo em `engdta.aula_bq.srag_2026`: semana epi vs mês.

-- 1. Casos por semana epidemiológica
SELECT SEM_NOT AS semana_epi, COUNT(*) AS casos
FROM `engdta.aula_bq.srag_2026`
GROUP BY semana_epi
ORDER BY semana_epi;

-- 2. Casos por mês
SELECT DATE_TRUNC(DATE(DT_NOTIFIC), MONTH) AS mes, COUNT(*) AS casos
FROM `engdta.aula_bq.srag_2026`
GROUP BY mes
ORDER BY mes;

-- 3. Semana epi vs mês

SELECT SEM_NOT AS semana_epi,
       DATE_TRUNC(DATE(DT_NOTIFIC), MONTH) AS mes,
       COUNT(*) AS casos
FROM `engdta.aula_bq.srag_2026`
GROUP BY semana_epi, mes
ORDER BY semana_epi, mes;
