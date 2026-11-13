"""
Módulo de coleta de publicações e comentários públicos do Instagram via Apify.
Actor principal verificado: apify/instagram-hashtag-scraper (com suporte a apify/instagram-scraper).
"""

import copy
import json
import re
from typing import Any, Dict, List, Optional
import unicodedata

from coleta.apify_client import ApifyClientError, ApifyIntegrationClient
from config.settings import (
    APIFY_INSTAGRAM_ACTOR_ID,
    INSTAGRAM_MAX_ITEMS,
    RAW_INSTAGRAM_DIR,
    get_logger,
    get_search_keywords,
    load_actor_config,
)

logger = get_logger("coleta.coletar_instagram")

MAPA_HASHTAGS_DOMINIO: Dict[str, List[str]] = {
    "sistema erp": ["sistemaerp", "erpsistema"],
    "software de gestao empresarial": ["gestaoempresarial", "softwaredegestao"],
    "implantacao de erp": ["implantacaoerp", "consultoriaerp"],
    "suporte tecnico de sistemas": ["suportetecnico", "sistemadegestao"],
    "dificuldades com erp": ["gestaodeprocessos", "automacaocomercial"],
    "automacao empresarial": ["automacaoempresarial", "automacaodeprocessos"],
}


def keyword_to_instagram_query(keyword: str) -> str:
    """
    Converte uma palavra-chave em termo/hashtag sem acentos e sem espaços
    compatível com o Instagram (ex: 'Implantação de ERP' -> 'implantacaodeerp').
    """
    nfkd = unicodedata.normalize("NFKD", keyword.strip().lower())
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    cleaned = re.sub(r"[^\w\s]", "", sem_acento)
    return re.sub(r"\s+", "", cleaned)


def build_instagram_input(
    keyword: str,
    max_items: int = INSTAGRAM_MAX_ITEMS,
    actor_id: str = APIFY_INSTAGRAM_ACTOR_ID,
) -> Dict[str, Any]:
    """
    Monta o payload específico para o Actor do Instagram configurado:
    - `apify/instagram-hashtag-scraper`: usa `hashtags`, `resultsType` e `resultsLimit`.
    - `apify/instagram-scraper`: usa `search`, `searchType`, `resultsType` e `resultsLimit`.
    """
    config = load_actor_config("instagram")
    nfkd = unicodedata.normalize("NFKD", keyword.strip().lower())
    chave_norm = "".join(c for c in nfkd if not unicodedata.combining(c))
    tag_principal = keyword_to_instagram_query(keyword)
    hashtags_lista = MAPA_HASHTAGS_DOMINIO.get(chave_norm, [tag_principal])

    if "hashtag-scraper" in actor_id.lower():
        payload = copy.deepcopy(config["input_template"])
        payload["hashtags"] = hashtags_lista
        payload["resultsType"] = "posts"
        payload["resultsLimit"] = int(max_items)
        return payload

    legacy = copy.deepcopy(
        config.get(
            "legacy_scraper_template",
            {
                "search": "",
                "searchType": "hashtag",
                "resultsType": "posts",
                "resultsLimit": 15,
            },
        )
    )
    legacy["search"] = tag_principal
    legacy["resultsLimit"] = int(max_items)
    return legacy


def _ja_coletado_instagram(keyword: str) -> Optional[Dict[str, Any]]:
    """Verifica se já existe arquivo bruto válido para a palavra-chave em dados/brutos/instagram."""
    safe_kw = "".join(c if c.isalnum() else "_" for c in keyword.lower()).strip("_")[:35]
    for arq in sorted(RAW_INSTAGRAM_DIR.glob(f"instagram_{safe_kw}_*.json")):
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
            itens = dados.get("items", []) if isinstance(dados, dict) else dados
            if itens:
                return {
                    "success": True,
                    "cached": True,
                    "platform": "Instagram",
                    "actor_id": APIFY_INSTAGRAM_ACTOR_ID,
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


def coletar_instagram(
    keywords: Optional[List[str]] = None,
    max_items: int = INSTAGRAM_MAX_ITEMS,
    skip_existing: bool = True,
    client: Optional[ApifyIntegrationClient] = None,
) -> Dict[str, Any]:
    """
    Executa a coleta do Instagram para as palavras-chave configuradas.
    """
    use_cache = skip_existing and (client is None)
    apify = client or ApifyIntegrationClient()
    search_terms = keywords or get_search_keywords()
    actor_id = APIFY_INSTAGRAM_ACTOR_ID

    if "hashtag-scraper" in actor_id.lower():
        required_fields = ["hashtags", "resultsType", "resultsLimit"]
    else:
        required_fields = ["search", "searchType", "resultsType", "resultsLimit"]

    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    total_collected = 0

    for kw in search_terms:
        if use_cache:
            cached = _ja_coletado_instagram(kw)
            if cached:
                logger.info(
                    "Reutilizando coleta existente do Instagram para '%s' (%d itens em %s)",
                    kw,
                    cached["items_count"],
                    cached["raw_file"],
                )
                results.append(cached)
                total_collected += cached["items_count"]
                continue

        try:
            run_input = build_instagram_input(
                keyword=kw, max_items=max_items, actor_id=actor_id
            )
            res = apify.execute_platform_actor(
                platform="Instagram",
                actor_id=actor_id,
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
