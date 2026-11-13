"""
Módulo de coleta de publicações e comentários públicos do Instagram via Apify.
Actor principal verificado: apify/instagram-scraper
"""

import copy
import re
from typing import Any, Dict, List, Optional

from coleta.apify_client import ApifyClientError, ApifyIntegrationClient
from config.settings import (
    APIFY_INSTAGRAM_ACTOR_ID,
    INSTAGRAM_MAX_ITEMS,
    get_logger,
    get_search_keywords,
    load_actor_config,
)

logger = get_logger("coleta.coletar_instagram")


def keyword_to_instagram_query(keyword: str) -> str:
    """
    Converte uma palavra-chave em termo compatível com a busca por hashtag/termo
    do apify/instagram-scraper (ex: 'Sistema ERP' -> 'sistemaerp').
    """
    cleaned = re.sub(r"[^\w\s]", "", keyword.strip().lower())
    return re.sub(r"\s+", "", cleaned)


def build_instagram_input(keyword: str, max_items: int = INSTAGRAM_MAX_ITEMS) -> Dict[str, Any]:
    """Monta o payload específico para o Actor apify/instagram-scraper."""
    config = load_actor_config("instagram")
    payload = copy.deepcopy(config["input_template"])
    payload["search"] = keyword_to_instagram_query(keyword)
    payload["resultsLimit"] = int(max_items)
    return payload


def coletar_instagram(
    keywords: Optional[List[str]] = None,
    max_items: int = INSTAGRAM_MAX_ITEMS,
    client: Optional[ApifyIntegrationClient] = None,
) -> Dict[str, Any]:
    """
    Executa a coleta do Instagram para as palavras-chave configuradas.
    Caso ocorra erro em uma palavra-chave ou limitação da plataforma, registra no log
    sem interromper a coleta das demais plataformas.
    """
    apify = client or ApifyIntegrationClient()
    search_terms = keywords or get_search_keywords()
    config = load_actor_config("instagram")
    required_fields = config.get("_meta", {}).get(
        "required_fields", ["search", "searchType", "resultsType", "resultsLimit"]
    )

    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    total_collected = 0

    for kw in search_terms:
        try:
            run_input = build_instagram_input(keyword=kw, max_items=max_items)
            res = apify.execute_platform_actor(
                platform="Instagram",
                actor_id=APIFY_INSTAGRAM_ACTOR_ID,
                run_input=run_input,
                keyword=kw,
                required_fields=required_fields,
            )
            results.append(res)
            total_collected += res["items_count"]
        except ApifyClientError as err:
            msg = f"Falha na coleta do Instagram para '{kw}': {err}"
            logger.error(msg)
            errors.append(msg)
        except Exception as exc:
            msg = f"Erro inesperado na coleta do Instagram para '{kw}': {exc}"
            logger.error(msg)
            errors.append(msg)

    return {
        "platform": "Instagram",
        "success": len(results) > 0 and len(errors) == 0,
        "partial_success": len(results) > 0 and len(errors) > 0,
        "total_items": total_collected,
        "runs": results,
        "errors": errors,
    }
