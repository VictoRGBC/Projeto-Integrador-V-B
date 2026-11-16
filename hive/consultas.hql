-- =============================================================================
-- PROJETO INTEGRADOR V - B | INTEGRA ENGENHARIA DE SISTEMAS
-- Consultas Analíticas em HiveQL (5 Obrigatórias + 7 Adicionais de Mercado)
-- =============================================================================

USE integra_mercado;

-- -----------------------------------------------------------------------------
-- CONSULTA 1 (OBRIGATÓRIA) — Distribuição de registros por plataforma
-- Objetivo: Identificar o volume de dados coletados (publicações e comentários)
-- em cada mídia social.
-- -----------------------------------------------------------------------------
SELECT
    plataforma,
    COUNT(*) AS total_registros,
    SUM(CASE WHEN tipo_registro = 'publicacao' THEN 1 ELSE 0 END) AS total_publicacoes,
    SUM(CASE WHEN tipo_registro = 'comentario' THEN 1 ELSE 0 END) AS total_comentarios,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentual_total
FROM inteligencia_mercado_social
WHERE plataforma IS NOT NULL AND plataforma <> ''
GROUP BY plataforma
ORDER BY total_registros DESC;

-- -----------------------------------------------------------------------------
-- CONSULTA 2 (OBRIGATÓRIA) — Distribuição de sentimentos
-- Objetivo: Identificar a quantidade e o percentual de registros positivos,
-- negativos e neutros (classificação heurística exploratória).
-- -----------------------------------------------------------------------------
SELECT
    sentimento,
    COUNT(*) AS total_registros,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentual
FROM inteligencia_mercado_social
WHERE sentimento IS NOT NULL AND sentimento <> ''
GROUP BY sentimento
ORDER BY total_registros DESC;

-- -----------------------------------------------------------------------------
-- CONSULTA 3 (OBRIGATÓRIA) — Assuntos mais recorrentes
-- Objetivo: Identificar os temas mais discutidos pelos usuários sobre sistemas
-- de gestão empresarial e ERP.
-- -----------------------------------------------------------------------------
SELECT
    assunto,
    COUNT(*) AS total_registros,
    SUM(CASE WHEN sentimento = 'Negativo' THEN 1 ELSE 0 END) AS registros_negativos,
    SUM(CASE WHEN sentimento = 'Positivo' THEN 1 ELSE 0 END) AS registros_positivos,
    SUM(CASE WHEN sentimento = 'Neutro' THEN 1 ELSE 0 END) AS registros_neutros,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentual_total
FROM inteligencia_mercado_social
WHERE assunto IS NOT NULL AND assunto <> ''
GROUP BY assunto
ORDER BY total_registros DESC;

-- -----------------------------------------------------------------------------
-- CONSULTA 4 (OBRIGATÓRIA) — Engajamento por plataforma
-- Objetivo: Analisar as métricas disponíveis por plataforma e tipo de registro,
-- respeitando suas diferenças de significado (likes vs upvotes vs views).
-- -----------------------------------------------------------------------------
SELECT
    plataforma,
    tipo_registro,
    COUNT(*) AS total_registros,
    SUM(CAST(NULLIF(TRIM(CAST(curtidas AS STRING)), '') AS BIGINT)) AS soma_curtidas_ou_votos,
    ROUND(AVG(CAST(NULLIF(TRIM(CAST(curtidas AS STRING)), '') AS BIGINT)), 2) AS media_curtidas_ou_votos,
    SUM(CAST(NULLIF(TRIM(CAST(comentarios AS STRING)), '') AS BIGINT)) AS soma_comentarios,
    SUM(CAST(NULLIF(TRIM(CAST(compartilhamentos AS STRING)), '') AS BIGINT)) AS soma_compartilhamentos,
    SUM(CAST(NULLIF(TRIM(CAST(visualizacoes AS STRING)), '') AS BIGINT)) AS soma_visualizacoes
FROM inteligencia_mercado_social
WHERE plataforma IS NOT NULL AND plataforma <> ''
GROUP BY plataforma, tipo_registro
ORDER BY plataforma, tipo_registro;

-- -----------------------------------------------------------------------------
-- CONSULTA 5 (OBRIGATÓRIA) — Evolução temporal
-- Objetivo: Identificar como o volume de publicações e comentários se comporta
-- ao longo do período analisado (por data de publicação).
-- -----------------------------------------------------------------------------
SELECT
    SUBSTR(data_publicacao, 1, 10) AS data_referencia,
    plataforma,
    tipo_registro,
    COUNT(*) AS total_registros
FROM inteligencia_mercado_social
WHERE data_publicacao IS NOT NULL AND LENGTH(TRIM(data_publicacao)) >= 10
GROUP BY SUBSTR(data_publicacao, 1, 10), plataforma, tipo_registro
ORDER BY data_referencia ASC, plataforma ASC;

-- -----------------------------------------------------------------------------
-- CONSULTA 6 (ADICIONAL) — Principais palavras-chave pesquisadas
-- Objetivo: Avaliar o volume de discussões e sentimentos por termo de busca.
-- -----------------------------------------------------------------------------
SELECT
    palavra_chave,
    COUNT(*) AS total_registros,
    SUM(CASE WHEN sentimento = 'Positivo' THEN 1 ELSE 0 END) AS positivos,
    SUM(CASE WHEN sentimento = 'Negativo' THEN 1 ELSE 0 END) AS negativos,
    SUM(CASE WHEN sentimento = 'Neutro' THEN 1 ELSE 0 END) AS neutros
FROM inteligencia_mercado_social
WHERE palavra_chave IS NOT NULL AND palavra_chave <> ''
GROUP BY palavra_chave
ORDER BY total_registros DESC;

-- -----------------------------------------------------------------------------
-- CONSULTA 7 (ADICIONAL) — Distribuição dos assuntos por plataforma
-- Objetivo: Comparar quais temas predominam em cada mídia social.
-- -----------------------------------------------------------------------------
SELECT
    plataforma,
    assunto,
    COUNT(*) AS total_registros
FROM inteligencia_mercado_social
WHERE plataforma IS NOT NULL AND assunto IS NOT NULL
GROUP BY plataforma, assunto
ORDER BY plataforma ASC, total_registros DESC;

-- -----------------------------------------------------------------------------
-- CONSULTA 8 (ADICIONAL) — Frequência de problemas relacionados a suporte
-- Objetivo: Investigar queixas e menções específicas sobre Atendimento e Suporte.
-- -----------------------------------------------------------------------------
SELECT
    plataforma,
    sentimento,
    COUNT(*) AS total_mencoes_suporte
FROM inteligencia_mercado_social
WHERE assunto = 'Atendimento e suporte'
   OR temas_adicionais LIKE '%Atendimento e suporte%'
GROUP BY plataforma, sentimento
ORDER BY total_mencoes_suporte DESC;

-- -----------------------------------------------------------------------------
-- CONSULTA 9 (ADICIONAL) — Frequência de problemas relacionados à implantação
-- Objetivo: Investigar relatos sobre Implantação, migração e treinamento de ERP.
-- -----------------------------------------------------------------------------
SELECT
    plataforma,
    sentimento,
    COUNT(*) AS total_mencoes_implantacao
FROM inteligencia_mercado_social
WHERE assunto = 'Implantação'
   OR temas_adicionais LIKE '%Implantação%'
GROUP BY plataforma, sentimento
ORDER BY total_mencoes_implantacao DESC;

-- -----------------------------------------------------------------------------
-- CONSULTA 10 (ADICIONAL) — Registros com maior quantidade de curtidas ou votos
-- Objetivo: Listar os Top 5 registros de maior destaque dentro de CADA plataforma
-- (sem comparar diretamente métricas incompatíveis entre plataformas distintas).
-- -----------------------------------------------------------------------------
SELECT
    plataforma,
    ranking_plataforma,
    tipo_registro,
    palavra_chave,
    assunto,
    sentimento,
    curtidas_ou_votos,
    url_publicacao,
    resumo_texto
FROM (
    SELECT
        plataforma,
        tipo_registro,
        palavra_chave,
        assunto,
        sentimento,
        CAST(NULLIF(TRIM(CAST(curtidas AS STRING)), '') AS BIGINT) AS curtidas_ou_votos,
        url_publicacao,
        SUBSTR(texto, 1, 140) AS resumo_texto,
        ROW_NUMBER() OVER (
            PARTITION BY plataforma
            ORDER BY CAST(NULLIF(TRIM(CAST(curtidas AS STRING)), '') AS BIGINT) DESC
        ) AS ranking_plataforma
    FROM inteligencia_mercado_social
    WHERE NULLIF(TRIM(CAST(curtidas AS STRING)), '') IS NOT NULL
) ranked_posts
WHERE ranking_plataforma <= 5
ORDER BY plataforma ASC, ranking_plataforma ASC;

-- -----------------------------------------------------------------------------
-- CONSULTA 11 (ADICIONAL) — Funcionalidades e módulos mais demandados no mercado
-- Objetivo: Identificar os módulos e funcionalidades individuais de ERP mais citados
-- (com desmembramento multivalorado e cálculo do Score de Criticidade ICP) para
-- orientar o roadmap de produto da Integra Engenharia de Sistemas.
-- -----------------------------------------------------------------------------
SELECT
    funcionalidade_individual AS funcionalidade,
    COUNT(*) AS total_mencoes,
    SUM(CASE WHEN sentimento = 'Positivo' THEN 1 ELSE 0 END) AS positivos,
    SUM(CASE WHEN sentimento = 'Negativo' THEN 1 ELSE 0 END) AS negativos,
    SUM(CASE WHEN sentimento = 'Neutro' THEN 1 ELSE 0 END) AS neutros,
    ROUND(SUM(CASE WHEN sentimento = 'Negativo' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS taxa_atrito_pct,
    ROUND(COUNT(*) + 1.5 * SUM(CASE WHEN sentimento = 'Negativo' THEN 1 ELSE 0 END), 1) AS score_icp
FROM inteligencia_funcionalidades_explodidas
GROUP BY funcionalidade_individual
ORDER BY total_mencoes DESC, score_icp DESC;

-- -----------------------------------------------------------------------------
-- CONSULTA 12 (ADICIONAL) — Principais dores e dificuldades operacionais relatadas
-- Objetivo: Mapear os gargalos individuais mais frequentes dos usuários de sistemas
-- empresariais (com Taxa de Atrito e Score de Criticidade ICP).
-- -----------------------------------------------------------------------------
SELECT
    dor_individual AS dor_operacional,
    COUNT(*) AS total_mencoes,
    SUM(CASE WHEN sentimento = 'Positivo' THEN 1 ELSE 0 END) AS positivos,
    SUM(CASE WHEN sentimento = 'Negativo' THEN 1 ELSE 0 END) AS relatos_negativos,
    SUM(CASE WHEN sentimento = 'Neutro' THEN 1 ELSE 0 END) AS neutros,
    ROUND(SUM(CASE WHEN sentimento = 'Negativo' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS taxa_atrito_pct,
    ROUND(COUNT(*) + 1.5 * SUM(CASE WHEN sentimento = 'Negativo' THEN 1 ELSE 0 END), 1) AS score_icp
FROM inteligencia_dores_explodidas
GROUP BY dor_individual
ORDER BY total_mencoes DESC, score_icp DESC;
