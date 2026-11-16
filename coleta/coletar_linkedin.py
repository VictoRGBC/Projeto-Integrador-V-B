"""
Módulo de coleta de publicações e discussões corporativas B2B públicas do LinkedIn via Apify.
Actor principal verificado: apimaestro/linkedin-posts-search-scraper-no-cookies (sem necessidade de cookies/login).
Actor alternativo compatível: harvestapi/linkedin-post-search.
"""

import copy
import json
from typing import Any, Dict, List, Optional

from coleta.apify_client import ApifyClientError, ApifyIntegrationClient
from config.settings import (
    APIFY_LINKEDIN_ACTOR_ID,
    LINKEDIN_MAX_ITEMS,
    RAW_LINKEDIN_DIR,
    get_logger,
    get_search_keywords,
    load_actor_config,
)

logger = get_logger("coleta.coletar_linkedin")

# Mapeamento de termos de busca corporativos para garantir alta precisão semântica no LinkedIn
# (evitando falsos positivos de preposições ou termos genéricos sem relação com ERP/gestão)
KEYWORD_LINKEDIN_QUERY_MAP: Dict[str, str] = {
    "sistema erp": "Sistema ERP",
    "software de gestão empresarial": "ERP software gestao",
    "software de gestao empresarial": "ERP software gestao",
    "implantação de erp": "Implantação de ERP",
    "implantacao de erp": "Implantação de ERP",
    "suporte técnico de sistemas": "ERP support",
    "suporte tecnico de sistemas": "ERP support",
    "dificuldades com erp": "ERP challenges problems",
    "automação empresarial": "ERP automation",
    "automacao empresarial": "ERP automation",
}


def build_linkedin_input(
    keyword: str,
    max_items: int = LINKEDIN_MAX_ITEMS,
    actor_id: str = APIFY_LINKEDIN_ACTOR_ID,
) -> Dict[str, Any]:
    """
    Monta o payload específico para o Actor do LinkedIn:
    - `apimaestro/linkedin-posts-search-scraper-no-cookies`: usa `keyword`, `limit`, `sort_type`, `page_number`.
    - `harvestapi/linkedin-post-search`: usa `searchQueries`, `maxPosts`, `sortBy`.
    """
    kw_clean = keyword.strip()
    search_term = KEYWORD_LINKEDIN_QUERY_MAP.get(kw_clean.lower(), kw_clean)

    if "harvestapi" in actor_id.lower():
        return {
            "searchQueries": [search_term],
            "maxPosts": int(max_items),
            "sortBy": "relevance",
        }

    config = load_actor_config("linkedin")
    payload = copy.deepcopy(config["input_template"])
    payload["keyword"] = search_term
    payload["limit"] = min(int(max_items), 50)
    return payload


def _ja_coletado_linkedin(keyword: str) -> Optional[Dict[str, Any]]:
    """Verifica se já existe arquivo bruto válido para a palavra-chave em dados/brutos/linkedin."""
    safe_kw = "".join(c if c.isalnum() else "_" for c in keyword.lower()).strip("_")[:35]
    for arq in sorted(RAW_LINKEDIN_DIR.glob(f"linkedin_{safe_kw}_*.json")):
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
            itens = dados.get("items", []) if isinstance(dados, dict) else dados
            if itens:
                return {
                    "success": True,
                    "cached": True,
                    "platform": "LinkedIn",
                    "actor_id": APIFY_LINKEDIN_ACTOR_ID,
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


def coletar_linkedin(
    keywords: Optional[List[str]] = None,
    max_items: int = LINKEDIN_MAX_ITEMS,
    skip_existing: bool = True,
    client: Optional[ApifyIntegrationClient] = None,
) -> Dict[str, Any]:
    """
    Executa a coleta do LinkedIn para as palavras-chave configuradas, com fallback
    automático entre Actors gratuitos compatíveis (`apimaestro` e `harvestapi`) caso necessário.
    """
    use_cache = skip_existing and (client is None)
    apify = client or ApifyIntegrationClient()
    search_terms = keywords or get_search_keywords()
    actor_id = APIFY_LINKEDIN_ACTOR_ID
    fallback_actor_id = "harvestapi/linkedin-post-search"

    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    total_collected = 0

    for kw in search_terms:
        if use_cache:
            cached = _ja_coletado_linkedin(kw)
            if cached:
                logger.info(
                    "Reutilizando coleta existente do LinkedIn para '%s' (%d itens em %s)",
                    kw,
                    cached["items_count"],
                    cached["raw_file"],
                )
                results.append(cached)
                total_collected += cached["items_count"]
                continue

        required_fields = (
            ["searchQueries", "maxPosts"]
            if "harvestapi" in actor_id.lower()
            else ["keyword", "limit"]
        )

        try:
            run_input = build_linkedin_input(
                keyword=kw,
                max_items=max_items,
                actor_id=actor_id,
            )
            res = apify.execute_platform_actor(
                platform="LinkedIn",
                actor_id=actor_id,
                run_input=run_input,
                keyword=kw,
                required_fields=required_fields,
            )
            results.append(res)
            total_collected += res["items_count"]
        except ApifyClientError as err:
            if client is None and actor_id != fallback_actor_id:
                logger.warning(
                    "Actor primário do LinkedIn (%s) falhou para '%s' (%s). Tentando Actor alternativo '%s'...",
                    actor_id,
                    kw,
                    err,
                    fallback_actor_id,
                )
                try:
                    fb_input = build_linkedin_input(
                        keyword=kw,
                        max_items=max_items,
                        actor_id=fallback_actor_id,
                    )
                    res_fb = apify.execute_platform_actor(
                        platform="LinkedIn",
                        actor_id=fallback_actor_id,
                        run_input=fb_input,
                        keyword=kw,
                        required_fields=["searchQueries", "maxPosts"],
                    )
                    actor_id = fallback_actor_id
                    results.append(res_fb)
                    total_collected += res_fb["items_count"]
                    continue
                except Exception as fb_err:
                    err = ApifyClientError(f"{err} | Fallback: {fb_err}")

            msg = f"Falha na coleta do LinkedIn para '{kw}': {err}"
            logger.error(msg)
            errors.append(msg)
        except Exception as exc:
            msg = f"Erro inesperado na coleta do LinkedIn para '{kw}': {exc}"
            logger.error(msg)
            errors.append(msg)

    return {
        "platform": "LinkedIn",
        "success": len(results) > 0 and len(errors) == 0,
        "partial_success": len(results) > 0 and len(errors) > 0,
        "total_items": total_collected,
        "runs": results,
        "errors": errors,
    }
