"""
Orquestrador Principal do Projeto Integrador V – B (Seção 9).
Sistema Multiplataforma de Inteligência de Mercado — Integra Engenharia de Sistemas.

Exemplos de execução modular:
  python main.py --validar
  python main.py --coleta
  python main.py --tratamento
  python main.py --hdfs
  python main.py --hive
  python main.py --pipeline
"""

import argparse
import sys
from typing import Any, Dict

from coleta.coletar_instagram import coletar_instagram
from coleta.coletar_reddit import coletar_reddit
from coleta.coletar_youtube import coletar_youtube
from config.settings import get_logger, get_search_keywords, validate_environment
from hadoop.scripts.enviar_hdfs import HdfsError, executar_fluxo_hdfs
from hive.executar_hive import HiveExecutionError, executar_fluxo_hive
from processamento.tratar_dados import executar_tratamento_completo

logger = get_logger("main")


def etapa_verificar_configuracoes(require_token: bool = False) -> Dict[str, Any]:
    """1. Verifica configurações, variáveis de ambiente e arquivos JSON dos Actors."""
    logger.info("Etapa 1: Verificando configurações do ambiente e templates de Actors...")
    status = validate_environment(require_token=require_token)
    if not status["valid"]:
        for issue in status["issues"]:
            logger.error("Problema de configuração: %s", issue)
    else:
        logger.info(
            "Configurações validadas com sucesso. Palavras-chave configuradas: %d",
            status["keywords_count"],
        )
    return status


def etapa_coleta_multiplataforma() -> Dict[str, Any]:
    """
    2-5. Executa a coleta no YouTube, Instagram e Reddit via Apify e salva os dados brutos.
    A falha em uma plataforma é registrada no log e não interrompe as demais.
    """
    status_cfg = etapa_verificar_configuracoes(require_token=True)
    if not status_cfg["valid"]:
        raise RuntimeError(
            "Não foi possível iniciar a coleta: configure APIFY_API_TOKEN no arquivo .env."
        )

    keywords = get_search_keywords()
    logger.info("Iniciando coleta multiplataforma para %d palavras-chave...", len(keywords))

    logger.info("Etapa 2: Executando coleta no YouTube...")
    res_yt = coletar_youtube(keywords=keywords)

    logger.info("Etapa 3: Executando coleta no Instagram...")
    res_ig = coletar_instagram(keywords=keywords)

    logger.info("Etapa 4: Executando coleta no Reddit...")
    res_rd = coletar_reddit(keywords=keywords)

    total_geral = (
        res_yt.get("total_items", 0)
        + res_ig.get("total_items", 0)
        + res_rd.get("total_items", 0)
    )
    logger.info(
        "Etapa 5 concluída: Dados brutos salvos. Total coletado -> YouTube: %d | Instagram: %d | Reddit: %d (Total: %d)",
        res_yt.get("total_items", 0),
        res_ig.get("total_items", 0),
        res_rd.get("total_items", 0),
        total_geral,
    )

    return {
        "youtube": res_yt,
        "instagram": res_ig,
        "reddit": res_rd,
        "total_items": total_geral,
    }


def etapa_tratamento() -> int:
    """
    6-9. Normaliza os resultados, classifica sentimentos e assuntos, consolida os registros
    e salva o CSV tratado em dados/tratados/dados_multiplataforma.csv.
    """
    logger.info("Etapas 6 a 9: Normalizando, classificando e consolidando registros...")
    df = executar_tratamento_completo()
    logger.info("Total de registros consolidados no CSV tratado: %d", len(df))
    return len(df)


def etapa_hdfs() -> Dict[str, Any]:
    """
    10. Envia os dados brutos e tratados para o Apache Hadoop / HDFS.
    """
    logger.info("Etapa 10: Enviando dados tratados para o HDFS...")
    res = executar_fluxo_hdfs()
    logger.info(
        "Armazenamento no HDFS concluído (%d arquivos transferidos).",
        len(res.get("uploaded_files", [])),
    )
    return res


def etapa_hive() -> Dict[str, Any]:
    """
    11. Disponibiliza os dados na tabela externa do Apache Hive e executa as consultas HiveQL.
    """
    logger.info("Etapa 11: Criando tabela externa e executando consultas analíticas no Apache Hive...")
    res = executar_fluxo_hive()
    logger.info("Consultas HiveQL concluídas. Resultados salvos em: %s", res.get("results_file"))
    return res


def executar_pipeline_completo() -> int:
    """
    Executa o fluxo completo na ordem definida na Seção 9 (Etapas 1 a 11).
    """
    logger.info("=== INICIANDO PIPELINE COMPLETO DE INTELIGÊNCIA DE MERCADO ===")
    try:
        etapa_coleta_multiplataforma()
    except Exception as err:
        logger.error("Erro na etapa de coleta: %s", err)
        return 1

    total_tratados = etapa_tratamento()
    if total_tratados == 0:
        logger.warning(
            "Nenhum registro tratado foi gerado. Verifique os logs de coleta ou adicione dados brutos."
        )

    try:
        etapa_hdfs()
        etapa_hive()
    except (HdfsError, HiveExecutionError) as infra_err:
        logger.error(
            "Aviso de infraestrutura Big Data (Hadoop/HDFS ou Hive): %s", infra_err
        )
        return 2

    logger.info("=== PIPELINE COMPLETO FINALIZADO COM SUCESSO ===")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Orquestrador do Sistema Multiplataforma de Inteligência de Mercado (Integra Engenharia)."
    )
    parser.add_argument(
        "--validar",
        action="store_true",
        help="Valida diretórios, arquivos de configuração dos Actors e variáveis de ambiente.",
    )
    parser.add_argument(
        "--coleta",
        action="store_true",
        help="Executa a coleta de dados públicos no YouTube, Instagram e Reddit via Apify.",
    )
    parser.add_argument(
        "--tratamento",
        action="store_true",
        help="Executa normalização, classificação heurística e consolidação do CSV tratado.",
    )
    parser.add_argument(
        "--hdfs",
        action="store_true",
        help="Cria diretórios e envia os dados tratados ao Apache Hadoop / HDFS.",
    )
    parser.add_argument(
        "--hive",
        action="store_true",
        help="Cria a tabela externa no Apache Hive e executa as consultas HiveQL.",
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Executa o fluxo completo (Coleta -> Tratamento -> HDFS -> Hive).",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if not any([args.validar, args.coleta, args.tratamento, args.hdfs, args.hive, args.pipeline]):
        parser.print_help()
        return 0

    if args.pipeline:
        return executar_pipeline_completo()

    exit_code = 0

    if args.validar:
        status = etapa_verificar_configuracoes(require_token=False)
        print("Status da configuração:", status)
        if not status["valid"]:
            exit_code = 1

    if args.coleta:
        try:
            etapa_coleta_multiplataforma()
        except Exception as err:
            logger.error("Falha na coleta: %s", err)
            exit_code = 1

    if args.tratamento:
        etapa_tratamento()

    if args.hdfs:
        try:
            etapa_hdfs()
        except HdfsError as err:
            logger.error("Falha no envio ao HDFS: %s", err)
            exit_code = 2

    if args.hive:
        try:
            etapa_hive()
        except HiveExecutionError as err:
            logger.error("Falha na execução do Hive: %s", err)
            exit_code = 2

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
