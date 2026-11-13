-- =============================================================================
-- PROJETO INTEGRADOR V - B | INTEGRA ENGENHARIA DE SISTEMAS
-- Script DDL HiveQL: Criação da Tabela Externa no Apache Hive sobre o HDFS
-- Localização HDFS: /projeto_integrador/dados_tratados/multiplataforma
-- =============================================================================

CREATE DATABASE IF NOT EXISTS integra_mercado
COMMENT 'Base analítica de Inteligência de Mercado Multiplataforma - Integra Engenharia de Sistemas';

USE integra_mercado;

DROP TABLE IF EXISTS inteligencia_mercado_social;

CREATE EXTERNAL TABLE IF NOT EXISTS inteligencia_mercado_social (
    plataforma          STRING COMMENT 'Origem do registro (YouTube, Instagram, Reddit)',
    tipo_registro       STRING COMMENT 'publicacao ou comentario',
    id_registro         STRING COMMENT 'Identificador original do registro na plataforma',
    id_publicacao       STRING COMMENT 'Identificador da publicacao original',
    texto               STRING COMMENT 'Conteudo textual padronizado e pseudonimizado',
    data_publicacao     STRING COMMENT 'Data original da publicacao em formato ISO 8601',
    data_coleta         STRING COMMENT 'Data da coleta em formato ISO 8601',
    palavra_chave       STRING COMMENT 'Termo utilizado na pesquisa no Apify',
    curtidas            BIGINT COMMENT 'Quantidade de curtidas ou votos positivos (upvotes), quando disponivel',
    comentarios         BIGINT COMMENT 'Quantidade de comentarios ou respostas, quando disponivel',
    compartilhamentos   BIGINT COMMENT 'Quantidade de compartilhamentos ou crossposts, quando disponivel',
    visualizacoes       BIGINT COMMENT 'Quantidade de visualizacoes ou reproducoes, quando disponivel',
    url_publicacao      STRING COMMENT 'Link publico da publicacao ou comentario',
    sentimento          STRING COMMENT 'Classificacao heuristica exploratoria (Positivo, Negativo, Neutro)',
    assunto             STRING COMMENT 'Categoria tematica principal identificada',
    temas_adicionais    STRING COMMENT 'Categorias tematicas secundarias identificadas',
    id_execucao         STRING COMMENT 'Identificador da execucao (runId) no Apify',
    actor_id            STRING COMMENT 'Identificador do Actor utilizado no Apify',
    origem_dado         STRING COMMENT 'Rastreabilidade da fonte de coleta',
    status_tratamento   STRING COMMENT 'Status do processamento e classificacao'
)
COMMENT 'Tabela externa consolidada de inteligencia de mercado multiplataforma'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    "separatorChar" = ",",
    "quoteChar"     = "\"",
    "escapeChar"    = "\\"
)
STORED AS TEXTFILE
LOCATION '/projeto_integrador/dados_tratados/multiplataforma'
TBLPROPERTIES (
    "skip.header.line.count" = "1",
    "serialization.null.format" = ""
);
