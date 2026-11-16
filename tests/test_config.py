"""
Testes unitários da FASE 1 — Configuração e Arquitetura.
"""

from config.settings import (
    ACTORS_CONFIG_DIR,
    DEFAULT_KEYWORDS,
    PROCESSED_DATA_DIR,
    RAW_INSTAGRAM_DIR,
    RAW_LINKEDIN_DIR,
    RAW_REDDIT_DIR,
    RAW_YOUTUBE_DIR,
    get_search_keywords,
    load_actor_config,
    validate_environment,
)


def test_directories_exist():
    """Verifica se a estrutura obrigatória de diretórios foi criada."""
    assert RAW_YOUTUBE_DIR.exists()
    assert RAW_INSTAGRAM_DIR.exists()
    assert RAW_REDDIT_DIR.exists()
    assert RAW_LINKEDIN_DIR.exists()
    assert PROCESSED_DATA_DIR.exists()
    assert ACTORS_CONFIG_DIR.exists()


def test_default_search_keywords():
    """Verifica se as 6 palavras-chave iniciais obrigatórias estão presentes."""
    keywords = get_search_keywords()
    assert len(keywords) >= 6
    assert "Sistema ERP" in keywords
    assert "Implantação de ERP" in keywords
    assert "Suporte técnico de sistemas" in keywords


def test_actor_configs_differ_and_have_templates():
    """
    Garante que cada plataforma possui configuração de Actor própria e distinta,
    sem usar o mesmo JSON genérico para todas.
    """
    yt_cfg = load_actor_config("youtube")
    ig_cfg = load_actor_config("instagram")
    rd_cfg = load_actor_config("reddit")
    li_cfg = load_actor_config("linkedin")

    assert "searchQueries" in yt_cfg["input_template"]
    assert "hashtags" in ig_cfg["input_template"]
    assert "searchQuery" in rd_cfg["input_template"]
    assert "keyword" in li_cfg["input_template"]

    # Verifica que os templates não são idênticos
    assert set(yt_cfg["input_template"].keys()) != set(ig_cfg["input_template"].keys())
    assert set(ig_cfg["input_template"].keys()) != set(rd_cfg["input_template"].keys())
    assert set(rd_cfg["input_template"].keys()) != set(li_cfg["input_template"].keys())


def test_validate_environment_structure():
    """Verifica a validação estrutural do ambiente (sem exigir token nos testes unitários)."""
    status = validate_environment(require_token=False)
    assert status["valid"] is True
    assert status["actors"]["youtube"]
    assert status["actors"]["instagram"]
    assert status["actors"]["reddit"]
    assert status["actors"]["linkedin"]
