"""
Testes unitários da FASE 2 — Coleta Multiplataforma com Apify.
Valida construção de payloads, validação de parâmetros, normalização de Actor ID,
persistência de JSON bruto e resiliência quando uma plataforma falha.
"""

import json
from pathlib import Path
import tempfile
from unittest.mock import MagicMock

from coleta.apify_client import ApifyClientError, ApifyIntegrationClient
from coleta.coletar_instagram import build_instagram_input, coletar_instagram
from coleta.coletar_linkedin import build_linkedin_input, coletar_linkedin
from coleta.coletar_reddit import build_reddit_input, coletar_reddit
from coleta.coletar_youtube import build_youtube_input, coletar_youtube


def test_actor_id_normalization():
    """Verifica conversão de 'owner/actor' para 'owner~actor' na API REST do Apify."""
    assert (
        ApifyIntegrationClient.normalize_actor_id_for_url("streamers/youtube-scraper")
        == "streamers~youtube-scraper"
    )
    assert (
        ApifyIntegrationClient.normalize_actor_id_for_url("apify/instagram-scraper")
        == "apify~instagram-scraper"
    )
    assert (
        ApifyIntegrationClient.normalize_actor_id_for_url("trudax/reddit-scraper-lite")
        == "trudax~reddit-scraper-lite"
    )


def test_platform_specific_inputs():
    """Garante que os payloads gerados respeitam a assinatura específica de cada Actor."""
    yt_in = build_youtube_input("Sistema ERP", max_items=15)
    assert yt_in["searchQueries"] == ["Sistema ERP"]
    assert yt_in["maxResults"] == 15

    ig_in = build_instagram_input(
        "Sistema ERP", max_items=12, actor_id="apify/instagram-hashtag-scraper"
    )
    assert "sistemaerp" in ig_in["hashtags"]
    assert ig_in["resultsLimit"] == 12
    assert ig_in["resultsType"] == "posts"

    rd_in = build_reddit_input(
        "Implantação de ERP",
        max_items=25,
        max_comments=8,
        actor_id="automation-lab/reddit-scraper",
    )
    assert rd_in["searchQuery"] == "Implantação de ERP"
    assert rd_in["maxPostsPerSource"] == 25
    assert rd_in["maxCommentsPerPost"] == 8

    li_in = build_linkedin_input(
        "Sistema ERP",
        max_items=15,
        actor_id="apimaestro/linkedin-posts-search-scraper-no-cookies",
    )
    assert li_in["keyword"] == "Sistema ERP"
    assert li_in["limit"] == 15
    assert li_in["sort_type"] == "relevance"


def test_validate_input_parameters_raises_on_missing():
    """Verifica se campos obrigatórios ausentes ou vazios disparam ApifyClientError."""
    try:
        ApifyIntegrationClient.validate_input_parameters(
            "YouTube", {"searchQueries": []}, ["searchQueries", "maxResults"]
        )
        assert False, "Deveria ter lançado ApifyClientError"
    except ApifyClientError as err:
        assert "searchQueries" in str(err)


def test_save_raw_dataset_preserves_original_and_meta():
    """Verifica se save_raw_dataset cria arquivo JSON com metadados e campos originais intactos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        raw_items = [{"id": "yt123", "title": "ERP na prática", "viewCount": 1200}]
        saved_file = ApifyIntegrationClient.save_raw_dataset(
            platform="YouTube",
            actor_id="streamers/youtube-scraper",
            run_id="run_abc123456",
            keyword="Sistema ERP",
            items=raw_items,
            output_dir=tmp_path,
        )
        assert saved_file.exists()
        content = json.loads(saved_file.read_text(encoding="utf-8"))
        assert content["metadata"]["plataforma"] == "YouTube"
        assert content["metadata"]["total_registros"] == 1
        assert content["items"][0]["id"] == "yt123"
        assert content["items"][0]["_coleta_meta"]["id_execucao"] == "run_abc123456"


def test_platform_failure_isolation():
    """
    Garante que a falha na coleta do Instagram não impede a coleta de YouTube e Reddit.
    """
    failing_client = MagicMock(spec=ApifyIntegrationClient)
    failing_client.execute_platform_actor.side_effect = ApifyClientError(
        "Simulação de bloqueio ou falta de créditos no Actor"
    )

    ig_res = coletar_instagram(keywords=["Sistema ERP"], client=failing_client)
    assert ig_res["success"] is False
    assert len(ig_res["errors"]) == 1

    ok_client = MagicMock(spec=ApifyIntegrationClient)
    ok_client.execute_platform_actor.return_value = {
        "success": True,
        "platform": "YouTube",
        "actor_id": "streamers/youtube-scraper",
        "run_id": "run_ok_1",
        "dataset_id": "ds_ok_1",
        "keyword": "Sistema ERP",
        "items_count": 2,
        "raw_file": "dados/brutos/youtube/mock.json",
        "items": [{"id": "1"}, {"id": "2"}],
    }
    yt_res = coletar_youtube(keywords=["Sistema ERP"], client=ok_client)
    rd_res = coletar_reddit(keywords=["Sistema ERP"], client=ok_client)

    assert yt_res["success"] is True
    assert yt_res["total_items"] == 2
    assert rd_res["success"] is True
    assert rd_res["total_items"] == 2
