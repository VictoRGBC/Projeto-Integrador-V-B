"""
Módulo de coleta de publicações e comentários públicos do Reddit via Apify.
Actor principal verificado: trudax/reddit-scraper-lite
"""

import copy
from typing import Any, Dict, List, Optional

from coleta.apify_client import ApifyClientError, ApifyIntegrationClient
from config.settings import (
    APIFY_REDDIT_ACTOR_ID,
    REDDIT_MAX_COMMENTS,
    REDDIT_MAX_ITEMS,
    get_logger,
    get_search_keywords,
    load_actor_config,
)

logger = get_logger("coleta.coletar_reddit")


def build_reddit_input(
    keyword: str,
    max_items: int = REDDIT_MAX_ITEMS,
    max_comments: int = REDDIT_MAX_COMMENTS,
) -> Dict[str, Any]:
    """Monta o payload específico para o Actor trudax/reddit-scraper-lite."""
    config = load_actor_config("reddit")
    payload = copy.deepcopy(config["input_template"])
    payload["searches"] = [keyword.strip()]
    payload["maxItems"] = int(max_items)
    payload["maxComments"] = int(max_comments)
    return payload


def coletar_reddit(
    keywords: Optional[List[str]] = None,
    max_items: int = REDDIT_MAX_ITEMS,
    max_comments: int = REDDIT_MAX_COMMENTS,
    client: Optional[ApifyIntegrationClient] = None,
) -> Dict[str, Any]:
    """
    Executa a coleta do Reddit para as palavras-chave configuradas.
    """
    apify = client or ApifyIntegrationClient()
    search_terms = keywords or get_search_keywords()
    config = load_actor_config("reddit")
    required_fields = config.get("_meta", {}).get("required_fields", ["searches", "maxItems"])

    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    total_collected = 0

    for kw in search_terms:
        try:
            run_input = build_reddit_input(
                keyword=kw, max_items=max_items, max_comments=max_comments
            )
            res = apify.execute_platform_actor(
                platform="Reddit",
                actor_id=APIFY_REDDIT_ACTOR_ID,
                run_input=run_input,
                keyword=kw,
                required_fields=required_fields,
            )
            results.append(res)
            total_collected += res["items_count"]
        except ApifyClientError as err:
            msg = f"Falha na coleta do Reddit para '{kw}': {err}"
            logger.error(msg)
            errors.append(msg)
        except Exception as exc:
            msg = f"Erro inesperado na coleta do Reddit para '{kw}': {exc}"
            logger.error(msg)
            errors.append(msg)

    return {
        "platform": "Reddit",
        "success": len(results) > 0 and len(errors) == 0,
        "partial_success": len(results) > 0 and len(errors) > 0,
        "total_items": total_collected,
        "runs": results,
        "errors": errors,
    }
