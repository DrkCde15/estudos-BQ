SELECT *
FROM `engdta.aula_bq.srag_2026`
LIMIT 30;

SELECT *
FROM `engdta.aula_bq.brasil_estados`
LIMIT 30;

SELECT *
FROM `engdta.aula_bq.brasil_total`
LIMIT 30;

SELECT COUNT(*) AS total_linhas_srag_2026
FROM `engdta.aula_bq.srag_2026`;

SELECT NU_NOTIFIC, DT_NOTIFIC, SG_UF_NOT, CS_SEXO, NU_IDADE_N
FROM `engdta.aula_bq.srag_2026`
LIMIT 30;


SELECT MIN(DT_NOTIFIC) AS primeira, MAX(DT_NOTIFIC) AS ultima
FROM `engdta.aula_bq.srag_2026`;


SELECT column_name, data_type
FROM `engdta.aula_bq.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'srag_2026'
ORDER BY ordinal_position;