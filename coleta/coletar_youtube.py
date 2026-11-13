"""
Módulo de coleta de vídeos e comentários públicos do YouTube via Apify.
Actor principal verificado: streamers/youtube-scraper
Actor complementar de comentários: streamers/youtube-comments-scraper
"""

import copy
import json
from typing import Any, Dict, List, Optional

from coleta.apify_client import ApifyClientError, ApifyIntegrationClient
from config.settings import (
    APIFY_YOUTUBE_ACTOR_ID,
    APIFY_YOUTUBE_COMMENTS_ACTOR_ID,
    RAW_YOUTUBE_DIR,
    YOUTUBE_MAX_COMMENTS,
    YOUTUBE_MAX_ITEMS,
    get_logger,
    get_search_keywords,
    load_actor_config,
)

logger = get_logger("coleta.coletar_youtube")


def build_youtube_input(keyword: str, max_items: int = YOUTUBE_MAX_ITEMS) -> Dict[str, Any]:
    """Monta o payload específico para o Actor streamers/youtube-scraper."""
    config = load_actor_config("youtube")
    payload = copy.deepcopy(config["input_template"])
    payload["searchQueries"] = [keyword.strip()]
    payload["maxResults"] = int(max_items)
    return payload


def build_youtube_comments_input(
    video_urls: List[str], max_comments: int = YOUTUBE_MAX_COMMENTS
) -> Dict[str, Any]:
    """Monta o payload específico para o Actor streamers/youtube-comments-scraper."""
    config = load_actor_config("youtube")
    payload = copy.deepcopy(config.get("comments_input_template", {}))
    payload["startUrls"] = [{"url": u} for u in video_urls if u]
    payload["maxComments"] = int(max_comments)
    return payload


def _ja_coletado_youtube(keyword: str) -> Optional[Dict[str, Any]]:
    """Verifica se já existe arquivo bruto válido para a palavra-chave em dados/brutos/youtube."""
    safe_kw = "".join(c if c.isalnum() else "_" for c in keyword.lower()).strip("_")[:35]
    for arq in sorted(RAW_YOUTUBE_DIR.glob(f"youtube_{safe_kw}_*.json")):
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
            itens = dados.get("items", []) if isinstance(dados, dict) else dados
            if itens:
                return {
                    "success": True,
                    "cached": True,
                    "platform": "YouTube",
                    "actor_id": APIFY_YOUTUBE_ACTOR_ID,
                    "run_id": "cached_on_disk",
                    "dataset_id": "cached_on_disk",
                    "keyword": keyword,
                    "items_count": len(itens),
                    "raw_file": str(arq),
                    "items": itens,
                }
        except Exception:
            continue
    return None


def coletar_youtube(
    keywords: Optional[List[str]] = None,
    max_items: int = YOUTUBE_MAX_ITEMS,
    collect_comments: bool = False,
    skip_existing: bool = True,
    client: Optional[ApifyIntegrationClient] = None,
) -> Dict[str, Any]:
    """
    Executa a coleta do YouTube para as palavras-chave configuradas.
    Reutiliza arquivos brutos já coletados para evitar consumo desnecessário de créditos
    quando `skip_existing=True` (exceto em testes unitários com `client` mockado).
    """
    use_cache = skip_existing and (client is None)
    apify = client or ApifyIntegrationClient()
    search_terms = keywords or get_search_keywords()
    config = load_actor_config("youtube")
    required_fields = config.get("_meta", {}).get("required_fields", ["searchQueries", "maxResults"])

    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    total_collected = 0

    for kw in search_terms:
        if use_cache:
            cached = _ja_coletado_youtube(kw)
            if cached:
                logger.info(
                    "Reutilizando coleta existente do YouTube para '%s' (%d itens em %s)",
                    kw,
                    cached["items_count"],
                    cached["raw_file"],
                )
                results.append(cached)
                total_collected += cached["items_count"]
                continue

        try:
            run_input = build_youtube_input(keyword=kw, max_items=max_items)
            res = apify.execute_platform_actor(
                platform="YouTube",
                actor_id=APIFY_YOUTUBE_ACTOR_ID,
                run_input=run_input,
                keyword=kw,
                required_fields=required_fields,
            )
            results.append(res)
            total_collected += res["items_count"]

            if collect_comments and res["items"]:
                video_urls = [
                    item.get("url")
                    for item in res["items"]
                    if isinstance(item, dict) and item.get("url")
                ][:2]
                if video_urls:
                    comments_input = build_youtube_comments_input(video_urls)
                    comments_res = apify.execute_platform_actor(
                        platform="YouTube",
                        actor_id=APIFY_YOUTUBE_COMMENTS_ACTOR_ID,
                        run_input=comments_input,
                        keyword=kw,
                        required_fields=["startUrls", "maxComments"],
                    )
                    results.append(comments_res)
                    total_collected += comments_res["items_count"]

        except ApifyClientError as err:
            msg = f"Falha na coleta do YouTube para '{kw}': {err}"
            logger.error(msg)
            errors.append(msg)
        except Exception as exc:
            msg = f"Erro inesperado na coleta do YouTube para '{kw}': {exc}"
            logger.error(msg)
            errors.append(msg)

    return {
        "platform": "YouTube",
        "success": len(results) > 0 and len(errors) == 0,
        "partial_success": len(results) > 0 and len(errors) > 0,
        "total_items": total_collected,
        "runs": results,
        "errors": errors,
    }
