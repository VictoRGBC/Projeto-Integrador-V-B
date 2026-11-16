"""
Módulo central de configurações do Projeto Integrador V - B.
Gerencia variáveis de ambiente, diretórios, palavras-chave e templates de Actors do Apify.
Suporta 4 plataformas: YouTube, Instagram, Reddit e LinkedIn.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis do arquivo .env se existir
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Diretórios de dados e logs
DATA_DIR = BASE_DIR / "dados"
RAW_DATA_DIR = DATA_DIR / "brutos"
RAW_YOUTUBE_DIR = RAW_DATA_DIR / "youtube"
RAW_INSTAGRAM_DIR = RAW_DATA_DIR / "instagram"
RAW_REDDIT_DIR = RAW_DATA_DIR / "reddit"
RAW_LINKEDIN_DIR = RAW_DATA_DIR / "linkedin"
PROCESSED_DATA_DIR = DATA_DIR / "tratados"
PROCESSED_CSV_PATH = PROCESSED_DATA_DIR / "dados_multiplataforma.csv"

CONFIG_DIR = BASE_DIR / "config"
ACTORS_CONFIG_DIR = CONFIG_DIR / "actors"
LOGS_DIR = BASE_DIR / "logs"
HADOOP_DIR = BASE_DIR / "hadoop"
HDFS_LOCAL_ROOT = HADOOP_DIR / "hdfs_storage"
HIVE_DIR = BASE_DIR / "hive"

# Garante que os diretórios essenciais existam
for directory in [
    RAW_YOUTUBE_DIR,
    RAW_INSTAGRAM_DIR,
    RAW_REDDIT_DIR,
    RAW_LINKEDIN_DIR,
    PROCESSED_DATA_DIR,
    ACTORS_CONFIG_DIR,
    LOGS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

# Credenciais e identificadores de Actors do Apify
APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "").strip()

APIFY_YOUTUBE_ACTOR_ID: str = os.getenv(
    "APIFY_YOUTUBE_ACTOR_ID", "streamers/youtube-scraper"
).strip()
APIFY_YOUTUBE_COMMENTS_ACTOR_ID: str = os.getenv(
    "APIFY_YOUTUBE_COMMENTS_ACTOR_ID", "streamers/youtube-comments-scraper"
).strip()
APIFY_INSTAGRAM_ACTOR_ID: str = os.getenv(
    "APIFY_INSTAGRAM_ACTOR_ID", "apify/instagram-hashtag-scraper"
).strip()
APIFY_REDDIT_ACTOR_ID: str = os.getenv(
    "APIFY_REDDIT_ACTOR_ID", "automation-lab/reddit-scraper"
).strip()
APIFY_LINKEDIN_ACTOR_ID: str = os.getenv(
    "APIFY_LINKEDIN_ACTOR_ID", "apimaestro/linkedin-posts-search-scraper-no-cookies"
).strip()

# Limites de itens por execução
YOUTUBE_MAX_ITEMS: int = int(os.getenv("YOUTUBE_MAX_ITEMS", "20"))
YOUTUBE_MAX_COMMENTS: int = int(os.getenv("YOUTUBE_MAX_COMMENTS", "10"))
INSTAGRAM_MAX_ITEMS: int = int(os.getenv("INSTAGRAM_MAX_ITEMS", "20"))
REDDIT_MAX_ITEMS: int = int(os.getenv("REDDIT_MAX_ITEMS", "20"))
REDDIT_MAX_COMMENTS: int = int(os.getenv("REDDIT_MAX_COMMENTS", "10"))
LINKEDIN_MAX_ITEMS: int = int(os.getenv("LINKEDIN_MAX_ITEMS", "20"))

# Parâmetros de controle de execução HTTP / Apify
APIFY_TIMEOUT_SECONDS: int = int(os.getenv("APIFY_TIMEOUT_SECONDS", "180"))
APIFY_MAX_RETRIES: int = int(os.getenv("APIFY_MAX_RETRIES", "3"))
APIFY_RETRY_BACKOFF_SECONDS: int = int(os.getenv("APIFY_RETRY_BACKOFF_SECONDS", "5"))

# Palavras-chave padrão do domínio de sistemas de gestão / ERP
DEFAULT_KEYWORDS: List[str] = [
    "Sistema ERP",
    "Software de gestão empresarial",
    "Implantação de ERP",
    "Suporte técnico de sistemas",
    "Dificuldades com ERP",
    "Automação empresarial",
]


def get_search_keywords() -> List[str]:
    """Retorna a lista de palavras-chave configuradas no .env ou a lista padrão."""
    raw_keywords = os.getenv("SEARCH_KEYWORDS", "").strip()
    if not raw_keywords:
        return list(DEFAULT_KEYWORDS)
    keywords = [kw.strip() for kw in raw_keywords.split(",") if kw.strip()]
    return keywords if keywords else list(DEFAULT_KEYWORDS)


# Configurações Hadoop / HDFS e Hive (execução direta sem Docker)
HDFS_BASE_DIR: str = os.getenv("HDFS_BASE_DIR", "/projeto_integrador")
HIVE_HOST: str = os.getenv("HIVE_HOST", "localhost")
HIVE_PORT: int = int(os.getenv("HIVE_PORT", "10000"))
HIVE_DATABASE: str = os.getenv("HIVE_DATABASE", "integra_mercado")


def load_actor_config(platform: str) -> Dict[str, Any]:
    """
    Carrega o arquivo JSON de configuração de entrada do Actor para a plataforma informada.
    Plataformas aceitas: 'youtube', 'instagram', 'reddit', 'linkedin'.
    """
    platform_key = platform.lower().strip()
    config_file = ACTORS_CONFIG_DIR / f"{platform_key}.json"
    if not config_file.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração do Actor não encontrado para '{platform}': {config_file}"
        )
    with open(config_file, mode="r", encoding="utf-8") as f:
        return json.load(f)


def get_logger(name: str) -> logging.Logger:
    """Configura e retorna um logger padronizado com saída em console e arquivo."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        log_file = LOGS_DIR / "pipeline.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def validate_environment(require_token: bool = False) -> Dict[str, Any]:
    """
    Valida a estrutura de diretórios, arquivos JSON dos Actors e variáveis de ambiente.
    """
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    token_now = os.getenv("APIFY_API_TOKEN", "").strip()
    issues: List[str] = []

    if require_token and not token_now:
        issues.append(
            "Variável APIFY_API_TOKEN não está definida no arquivo .env."
        )

    for platform in ("youtube", "instagram", "reddit", "linkedin"):
        cfg_path = ACTORS_CONFIG_DIR / f"{platform}.json"
        if not cfg_path.exists():
            issues.append(f"Arquivo de configuração ausente: {cfg_path}")
        else:
            try:
                data = load_actor_config(platform)
                if "input_template" not in data:
                    issues.append(
                        f"Chave 'input_template' ausente em {cfg_path.name}"
                    )
            except Exception as exc:
                issues.append(f"Erro ao ler {cfg_path.name}: {exc}")

    return {
        "valid": len(issues) == 0,
        "has_apify_token": bool(token_now),
        "actors": {
            "youtube": APIFY_YOUTUBE_ACTOR_ID,
            "instagram": APIFY_INSTAGRAM_ACTOR_ID,
            "reddit": APIFY_REDDIT_ACTOR_ID,
            "linkedin": APIFY_LINKEDIN_ACTOR_ID,
        },
        "keywords_count": len(get_search_keywords()),
        "issues": issues,
    }
