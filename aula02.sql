-- Aula 02 (SQL)

-- 1. Volume + janela temporal (revisão da aula01).
SELECT COUNT(*) AS total_linhas,
       MIN(DT_NOTIFIC) AS primeira_notific,
       MAX(DT_NOTIFIC) AS ultima_notific
FROM `engdta.aula_bq.srag_2026`;

-- 2. Cardinalidade: quantos valores distintos nas categóricas principais?
SELECT COUNT(DISTINCT SG_UF_NOT) AS ufs_distintas,
       COUNT(DISTINCT CS_SEXO) AS sexos_distintos,
       COUNT(DISTINCT SG_UF) AS ufs_residencia_distintas
FROM `engdta.aula_bq.srag_2026`;

-- 3. Top valores de sexo (esperado: M/F/I).
SELECT CS_SEXO, COUNT(*) AS n
FROM `engdta.aula_bq.srag_2026`
GROUP BY CS_SEXO
ORDER BY n DESC;

-- 4. Top 10 UFs notificantes.
SELECT SG_UF_NOT AS uf, COUNT(*) AS n
FROM `engdta.aula_bq.srag_2026`
GROUP BY uf
ORDER BY n DESC
LIMIT 10;

-- 5. Nulos nas colunas-chave (COUNTIF não conta nulo no COUNT simples).
SELECT COUNTIF(SG_UF_NOT IS NULL) AS uf_not_nulos,
       COUNTIF(CS_SEXO IS NULL) AS sexo_nulos,
       COUNTIF(DT_NASC IS NULL) AS nasc_nulos,
       COUNTIF(NU_IDADE_N IS NULL) AS idade_nulos,
       COUNTIF(DT_SIN_PRI IS NULL) AS sin_pri_nulos
FROM `engdta.aula_bq.srag_2026`;

-- 6. Idades: faixa e suspeitos.
SELECT MIN(NU_IDADE_N) AS idade_min,
       MAX(NU_IDADE_N) AS idade_max,
       AVG(NU_IDADE_N) AS idade_media,
       COUNTIF(NU_IDADE_N > 120) AS idades_impossiveis
FROM `engdta.aula_bq.srag_2026`;
