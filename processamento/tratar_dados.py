"""
Módulo de orquestração do tratamento, normalização, classificação e consolidação
dos dados brutos multiplataforma em CSV tratado (Seções 4 e 5).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from config.settings import (
    PROCESSED_CSV_PATH,
    PROCESSED_DATA_DIR,
    RAW_INSTAGRAM_DIR,
    RAW_LINKEDIN_DIR,
    RAW_REDDIT_DIR,
    RAW_YOUTUBE_DIR,
    get_logger,
)
from processamento.normalizar_dados import normalizar_registros

logger = get_logger("processamento.tratar_dados")


def carregar_json_brutos_plataforma(diretorio: Path) -> List[Dict[str, Any]]:
    """
    Carrega todos os arquivos .json de uma pasta de dados brutos (ex: dados/brutos/youtube).
    Suporta tanto o formato com envelope {"metadata": ..., "items": [...]} quanto listas diretas.
    """
    registros: List[Dict[str, Any]] = []
    if not diretorio.exists():
        return registros

    arquivos_json = sorted(diretorio.glob("*.json"))
    for arquivo in arquivos_json:
        try:
            with open(arquivo, mode="r", encoding="utf-8") as f:
                conteudo = json.load(f)

            if isinstance(conteudo, dict) and "items" in conteudo:
                meta_envelope = conteudo.get("metadata", {})
                itens = conteudo.get("items", [])
                for item in itens:
                    if isinstance(item, dict):
                        if "_coleta_meta" not in item and meta_envelope:
                            item["_coleta_meta"] = meta_envelope
                        registros.append(item)
            elif isinstance(conteudo, list):
                for item in conteudo:
                    if isinstance(item, dict):
                        registros.append(item)
        except Exception as exc:
            logger.error("Erro ao ler arquivo bruto %s: %s", arquivo, exc)

    return registros


def executar_tratamento_completo(
    raw_youtube_dir: Path = RAW_YOUTUBE_DIR,
    raw_instagram_dir: Path = RAW_INSTAGRAM_DIR,
    raw_reddit_dir: Path = RAW_REDDIT_DIR,
    raw_linkedin_dir: Path = RAW_LINKEDIN_DIR,
    output_csv_path: Path = PROCESSED_CSV_PATH,
) -> pd.DataFrame:
    """
    Carrega os JSONs brutos das quatro plataformas, normaliza, classifica sentimentos e temas,
    remove duplicidades e salva o CSV final consolidado em UTF-8-SIG (Seção 4.4).
    """
    logger.info("Iniciando carregamento dos dados brutos multiplataforma...")
    brutos_yt = carregar_json_brutos_plataforma(raw_youtube_dir)
    brutos_ig = carregar_json_brutos_plataforma(raw_instagram_dir)
    brutos_rd = carregar_json_brutos_plataforma(raw_reddit_dir)
    brutos_li = carregar_json_brutos_plataforma(raw_linkedin_dir)

    logger.info(
        "Registros brutos lidos -> YouTube: %d | Instagram: %d | Reddit: %d | LinkedIn: %d",
        len(brutos_yt),
        len(brutos_ig),
        len(brutos_rd),
        len(brutos_li),
    )

    df_consolidado = normalizar_registros(
        registros_youtube=brutos_yt,
        registros_instagram=brutos_ig,
        registros_reddit=brutos_rd,
        registros_linkedin=brutos_li,
    )

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    # Salva CSV principal em UTF-8-SIG para compatibilidade com Excel/Planilhas (Seção 4.4)
    df_consolidado.to_csv(output_csv_path, index=False, encoding="utf-8-sig")

    # Salva cópia em UTF-8 puro (sem BOM) para ingestão limpa no Apache Hive / HDFS
    hive_csv_path = output_csv_path.parent / "dados_multiplataforma_hive.csv"
    df_consolidado.to_csv(hive_csv_path, index=False, encoding="utf-8")

    logger.info(
        "Tratamento concluído com sucesso. Total de registros únicos normalizados: %d. Arquivo salvo em: %s",
        len(df_consolidado),
        output_csv_path,
    )
    return df_consolidado


def carregar_dados_tratados(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """Carrega o CSV tratado consolidado caso já exista em disco."""
    caminho = csv_path or PROCESSED_CSV_PATH
    if not caminho.exists():
        return normalizar_registros()
    df = pd.read_csv(caminho, encoding="utf-8-sig")
    for col in ["curtidas", "comentarios", "compartilhamentos", "visualizacoes"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df
