"""
Módulo de coleta de publicações e comentários públicos do Reddit via Apify.
Actor principal verificado: automation-lab/reddit-scraper (sem exigência de sessionToken).
Suporta também trudax/reddit-scraper-lite caso configurado pelo usuário.
"""

import copy
import json
from typing import Any, Dict, List, Optional

from coleta.apify_client import ApifyClientError, ApifyIntegrationClient
from config.settings import (
    APIFY_REDDIT_ACTOR_ID,
    RAW_REDDIT_DIR,
    REDDIT_MAX_COMMENTS,
    REDDIT_MAX_ITEMS,
    get_logger,
    get_search_keywords,
    load_actor_config,
)

logger = get_logger("coleta.coletar_reddit")

# Mapeamento de consultas para garantir foco no domínio de sistemas ERP no Reddit
KEYWORD_REDDIT_QUERY_MAP: Dict[str, str] = {
    "software de gestão empresarial": "ERP software business",
    "software de gestao empresarial": "ERP software business",
    "suporte técnico de sistemas": "ERP support implementation",
    "suporte tecnico de sistemas": "ERP support implementation",
    "automação empresarial": "ERP automation workflow",
    "automacao empresarial": "ERP automation workflow",
}


def build_reddit_input(
    keyword: str,
    max_items: int = REDDIT_MAX_ITEMS,
    max_comments: int = REDDIT_MAX_COMMENTS,
    actor_id: str = APIFY_REDDIT_ACTOR_ID,
) -> Dict[str, Any]:
    """
    Monta o payload específico para o Actor do Reddit:
    - `automation-lab/reddit-scraper`: usa `searchQuery`, `maxPostsPerSource`, `maxCommentsPerPost`.
    - `trudax/reddit-scraper-lite`: usa `searches`, `maxItems`, `maxComments`.
    """
    kw_clean = keyword.strip()
    search_term = KEYWORD_REDDIT_QUERY_MAP.get(kw_clean.lower(), kw_clean)

    if "trudax" in actor_id.lower():
        return {
            "searches": [search_term],
            "sort": "new",
            "time": "all",
            "maxItems": int(max_items),
            "maxPostCount": int(max_items),
            "maxComments": int(max_comments),
            "skipComments": False,
        }

    config = load_actor_config("reddit")
    payload = copy.deepcopy(config["input_template"])
    payload["searchQuery"] = search_term
    payload["maxPostsPerSource"] = int(max_items)
    payload["maxCommentsPerPost"] = int(max_comments)
    return payload


def _ja_coletado_reddit(keyword: str) -> Optional[Dict[str, Any]]:
    """Verifica se já existe arquivo bruto válido para a palavra-chave em dados/brutos/reddit."""
    safe_kw = "".join(c if c.isalnum() else "_" for c in keyword.lower()).strip("_")[:35]
    for arq in sorted(RAW_REDDIT_DIR.glob(f"reddit_{safe_kw}_*.json")):
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
            itens = dados.get("items", []) if isinstance(dados, dict) else dados
            if itens:
                return {
                    "success": True,
                    "cached": True,
                    "platform": "Reddit",
                    "actor_id": APIFY_REDDIT_ACTOR_ID,
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


def coletar_reddit(
    keywords: Optional[List[str]] = None,
    max_items: int = REDDIT_MAX_ITEMS,
    max_comments: int = REDDIT_MAX_COMMENTS,
    skip_existing: bool = True,
    client: Optional[ApifyIntegrationClient] = None,
) -> Dict[str, Any]:
    """
    Executa a coleta do Reddit para as palavras-chave configuradas.
    """
    use_cache = skip_existing and (client is None)
    apify = client or ApifyIntegrationClient()
    search_terms = keywords or get_search_keywords()
    actor_id = APIFY_REDDIT_ACTOR_ID

    if "trudax" in actor_id.lower():
        required_fields = ["searches", "maxItems"]
    else:
        required_fields = ["searchQuery", "maxPostsPerSource"]

    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    total_collected = 0

    for kw in search_terms:
        if use_cache:
            cached = _ja_coletado_reddit(kw)
            if cached:
                logger.info(
                    "Reutilizando coleta existente do Reddit para '%s' (%d itens em %s)",
                    kw,
                    cached["items_count"],
                    cached["raw_file"],
                )
                results.append(cached)
                total_collected += cached["items_count"]
                continue

        try:
            run_input = build_reddit_input(
                keyword=kw,
                max_items=max_items,
                max_comments=max_comments,
                actor_id=actor_id,
            )
            res = apify.execute_platform_actor(
                platform="Reddit",
                actor_id=actor_id,
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
