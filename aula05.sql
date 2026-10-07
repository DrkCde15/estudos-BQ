-- Aula 05 (SQL) — JOINs entre `srag_2026` e `brasil_total` (chave: UF).

-- 0. Auditoria de nulos na chave (rode antes de qualquer JOIN).
SELECT COUNTIF(SG_UF_NOT IS NULL) AS uf_nulos,
       COUNT(DISTINCT SG_UF_NOT) AS ufs_distintas,
       COUNT(*) AS total
FROM `engdta.aula_bq.srag_2026`;

-- 1. INNER JOIN: lado a lado, notificações SRAG vs totais COVID por UF.
-- Esperado: 27 linhas somando 9.999 — a linha nula evapora sem erro.
SELECT s.uf,
       s.casos_srag,
       b.deaths AS obitos_covid,
       b.totalCases AS casos_covid
FROM (SELECT SG_UF_NOT AS uf, COUNT(*) AS casos_srag
      FROM `engdta.aula_bq.srag_2026`
      GROUP BY uf) s
INNER JOIN `engdta.aula_bq.brasil_total` b
  ON b.state = s.uf
WHERE b.state != 'TOTAL'
ORDER BY s.casos_srag DESC;

-- 1b. Variante rotulando o desconhecido (COALESCE antes de agregar).
SELECT COALESCE(SG_UF_NOT, 'IGNORADO') AS uf, COUNT(*) AS casos
FROM `engdta.aula_bq.srag_2026`
GROUP BY uf
ORDER BY casos DESC;

-- 2. LEFT JOIN: UFs do consolidado SEM nenhuma notificação SRAG na amostra.

-- 2b. Verificação: menores coberturas (sem HAVING, para provar que há dados).
SELECT b.state AS uf, COUNT(s.SG_UF_NOT) AS casos_srag
FROM `engdta.aula_bq.brasil_total` b
LEFT JOIN `engdta.aula_bq.srag_2026` s
  ON s.SG_UF_NOT = b.state
WHERE b.state != 'TOTAL'
GROUP BY uf
ORDER BY casos_srag ASC
LIMIT 5;