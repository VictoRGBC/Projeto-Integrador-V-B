"""
Módulo centralizado de integração com a plataforma Apify (REST API v2 / SDK Oficial).
Responsável por validar Actors, parâmetros de entrada, executar coletas com retentativas
progressivas, aguardar conclusão controlada e persistir os datasets brutos em JSON.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import requests

from config.settings import (
    APIFY_API_TOKEN,
    APIFY_MAX_RETRIES,
    APIFY_RETRY_BACKOFF_SECONDS,
    APIFY_TIMEOUT_SECONDS,
    RAW_DATA_DIR,
    get_logger,
    load_actor_config,
)

logger = get_logger("coleta.apify_client")


class ApifyClientError(Exception):
    """Exceção específica para erros de integração com a API do Apify."""


class ApifyIntegrationClient:
    """
    Cliente centralizado para execução de Actors do Apify nas três plataformas
    (YouTube, Instagram e Reddit) utilizando a API REST v2 oficial do Apify.
    """

    BASE_URL = "https://api.apify.com/v2"
    TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}
    RETRYABLE_HTTP_CODES = {408, 429, 500, 502, 503, 504}

    def __init__(
        self,
        api_token: Optional[str] = None,
        timeout_seconds: int = APIFY_TIMEOUT_SECONDS,
        max_retries: int = APIFY_MAX_RETRIES,
        retry_backoff_seconds: int = APIFY_RETRY_BACKOFF_SECONDS,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_token = (api_token if api_token is not None else APIFY_API_TOKEN).strip()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.session = session or requests.Session()

    @staticmethod
    def normalize_actor_id_for_url(actor_id: str) -> str:
        """
        Converte identificadores no formato 'usuario/actor' para 'usuario~actor',
        conforme exigido pelos endpoints REST v2 do Apify.
        """
        cleaned = actor_id.strip()
        if not cleaned:
            raise ApifyClientError("O identificador do Actor (actor_id) está vazio.")
        return cleaned.replace("/", "~")

    def _check_token(self) -> None:
        if not self.api_token:
            raise ApifyClientError(
                "APIFY_API_TOKEN não configurado. Defina a variável no arquivo .env antes de executar a coleta."
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Executa uma requisição HTTP à API do Apify com retentativas e backoff progressivo
        para falhas temporárias de rede ou limites de taxa (HTTP 429 / 5xx).
        """
        self._check_token()
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.request(
                    method=method.upper(),
                    url=url,
                    headers=self._headers(),
                    params=params,
                    json=json_payload,
                    timeout=min(self.timeout_seconds, 60),
                )

                if response.status_code in self.RETRYABLE_HTTP_CODES:
                    wait_s = self.retry_backoff_seconds * attempt
                    logger.warning(
                        "HTTP %s recebido em %s (tentativa %s/%s). Aguardando %ss...",
                        response.status_code,
                        endpoint,
                        attempt,
                        self.max_retries,
                        wait_s,
                    )
                    if attempt < self.max_retries:
                        time.sleep(wait_s)
                        continue

                response.raise_for_status()
                return response

            except requests.exceptions.HTTPError as http_err:
                status_code = (
                    http_err.response.status_code
                    if http_err.response is not None
                    else "desconhecido"
                )
                error_detail = ""
                if http_err.response is not None:
                    try:
                        error_detail = http_err.response.json().get("error", {}).get("message", "")
                    except Exception:
                        error_detail = http_err.response.text[:250]

                logger.error(
                    "Erro HTTP %s na API do Apify (%s): %s",
                    status_code,
                    endpoint,
                    error_detail or str(http_err),
                )
                raise ApifyClientError(
                    f"Erro HTTP {status_code} ao acessar '{endpoint}': {error_detail or http_err}"
                ) from http_err

            except requests.exceptions.RequestException as req_err:
                last_error = req_err
                wait_s = self.retry_backoff_seconds * attempt
                logger.warning(
                    "Falha temporária de conexão em %s (tentativa %s/%s): %s",
                    endpoint,
                    attempt,
                    self.max_retries,
                    req_err,
                )
                if attempt < self.max_retries:
                    time.sleep(wait_s)

        raise ApifyClientError(
            f"Falha ao comunicar com a API do Apify após {self.max_retries} tentativas: {last_error}"
        )

    def validate_actor(self, actor_id: str) -> Dict[str, Any]:
        """
        Verifica se o Actor existe e está acessível na Apify Store / conta do usuário.
        """
        actor_slug = self.normalize_actor_id_for_url(actor_id)
        logger.info("Validando existência do Actor no Apify: %s", actor_id)
        resp = self._request_with_retry("GET", f"actors/{actor_slug}")
        data = resp.json().get("data", {})
        if not data:
            raise ApifyClientError(f"Actor '{actor_id}' retornou metadados vazios.")
        return data

    @staticmethod
    def validate_input_parameters(
        platform: str, payload: Dict[str, Any], required_fields: List[str]
    ) -> None:
        """
        Valida se todos os campos obrigatórios de entrada do Actor estão presentes e preenchidos.
        """
        missing = []
        for field in required_fields:
            if field not in payload:
                missing.append(field)
                continue
            val = payload[field]
            if val is None or (isinstance(val, (str, list, dict)) and len(val) == 0):
                missing.append(field)

        if missing:
            raise ApifyClientError(
                f"Parâmetros obrigatórios ausentes ou vazios para {platform}: {', '.join(missing)}"
            )

    def start_actor_run(self, actor_id: str, run_input: Dict[str, Any]) -> Dict[str, Any]:
        """Inicia uma execução (run) do Actor com o payload especificado."""
        actor_slug = self.normalize_actor_id_for_url(actor_id)
        logger.info("Iniciando execução do Actor '%s'...", actor_id)
        resp = self._request_with_retry(
            "POST",
            f"actors/{actor_slug}/runs",
            params={"timeout": self.timeout_seconds},
            json_payload=run_input,
        )
        run_data = resp.json().get("data", {})
        if not run_data or "id" not in run_data:
            raise ApifyClientError(
                f"Resposta inválida ao iniciar execução do Actor '{actor_id}'."
            )
        return run_data

    def wait_for_run(self, run_id: str, poll_interval: float = 4.0) -> Dict[str, Any]:
        """
        Aguarda de maneira controlada a conclusão da execução do Actor até atingir
        um status terminal ou o timeout configurado.
        """
        start_time = time.monotonic()
        while True:
            resp = self._request_with_retry("GET", f"actor-runs/{run_id}")
            run_data = resp.json().get("data", {})
            status = run_data.get("status", "UNKNOWN")

            if status in self.TERMINAL_STATUSES:
                if status == "TIMED-OUT" and run_data.get("defaultDatasetId"):
                    logger.warning(
                        "Execução '%s' atingiu TIMED-OUT no Apify, mas o dataset parcial '%s' será recuperado.",
                        run_id,
                        run_data.get("defaultDatasetId"),
                    )
                    return run_data
                if status != "SUCCEEDED":
                    raise ApifyClientError(
                        f"Execução '{run_id}' finalizou com status malsucedido: {status}"
                    )
                logger.info("Execução '%s' concluída com sucesso (SUCCEEDED).", run_id)
                return run_data

            elapsed = time.monotonic() - start_time
            if elapsed >= self.timeout_seconds:
                raise ApifyClientError(
                    f"Timeout ({self.timeout_seconds}s) excedido aguardando a execução '{run_id}' (status atual: {status})."
                )

            time.sleep(poll_interval)

    def fetch_dataset_items(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Recupera os itens do Dataset padrão gerado pela execução do Actor."""
        if not dataset_id:
            raise ApifyClientError("Identificador do dataset (defaultDatasetId) ausente.")
        logger.info("Recuperando itens do Dataset '%s'...", dataset_id)
        resp = self._request_with_retry(
            "GET",
            f"datasets/{dataset_id}/items",
            params={"format": "json", "clean": "false"},
        )
        items = resp.json()
        if not isinstance(items, list):
            raise ApifyClientError("Formato inesperado ao recuperar itens do Dataset.")
        logger.info("Dataset '%s' retornou %d registros.", dataset_id, len(items))
        return items

    @staticmethod
    def save_raw_dataset(
        platform: str,
        actor_id: str,
        run_id: str,
        keyword: str,
        items: List[Dict[str, Any]],
        output_dir: Optional[Path] = None,
    ) -> Path:
        """
        Salva os dados brutos em JSON preservando integralmente os campos originais
        e anexando metadados técnicos de auditoria (_coleta_meta).
        """
        platform_key = platform.lower().strip()
        target_dir = output_dir or (RAW_DATA_DIR / platform_key)
        target_dir.mkdir(parents=True, exist_ok=True)

        collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_kw = "".join(c if c.isalnum() else "_" for c in keyword.lower()).strip("_")[:35]
        filename = f"{platform_key}_{safe_kw or 'geral'}_{timestamp_slug}_{run_id[:8]}.json"
        file_path = target_dir / filename

        enriched_items: List[Dict[str, Any]] = []
        for item in items:
            record = dict(item)
            record["_coleta_meta"] = {
                "plataforma": platform,
                "actor_id": actor_id,
                "id_execucao": run_id,
                "palavra_chave": keyword,
                "data_coleta": collected_at,
                "origem_dado": f"apify:{actor_id}",
            }
            enriched_items.append(record)

        envelope = {
            "metadata": {
                "plataforma": platform,
                "actor_id": actor_id,
                "id_execucao": run_id,
                "palavra_chave": keyword,
                "data_coleta": collected_at,
                "total_registros": len(enriched_items),
            },
            "items": enriched_items,
        }

        with open(file_path, mode="w", encoding="utf-8") as f:
            json.dump(envelope, f, ensure_ascii=False, indent=2)

        logger.info(
            "Dados brutos de %s salvos em: %s (%d itens)",
            platform,
            file_path,
            len(enriched_items),
        )
        return file_path

    def execute_platform_actor(
        self,
        platform: str,
        actor_id: str,
        run_input: Dict[str, Any],
        keyword: str,
        required_fields: Optional[List[str]] = None,
        poll_interval: float = 4.0,
    ) -> Dict[str, Any]:
        """
        Fluxo completo padronizado para uma plataforma:
        1. Valida configuração e parâmetros obrigatórios
        2. Valida existência do Actor no Apify
        3. Executa o Actor
        4. Aguarda conclusão
        5. Recupera os dados do Dataset
        6. Salva dados brutos em JSON
        7. Retorna resumo da execução e registros coletados
        """
        if required_fields is None:
            cfg = load_actor_config(platform)
            required_fields = cfg.get("_meta", {}).get("required_fields", [])

        self.validate_input_parameters(platform, run_input, required_fields)
        self.validate_actor(actor_id)

        run_info = self.start_actor_run(actor_id, run_input)
        run_id = run_info["id"]
        completed_run = self.wait_for_run(run_id, poll_interval=poll_interval)
        dataset_id = completed_run.get("defaultDatasetId", "")

        items = self.fetch_dataset_items(dataset_id)
        saved_path = self.save_raw_dataset(
            platform=platform,
            actor_id=actor_id,
            run_id=run_id,
            keyword=keyword,
            items=items,
        )

        return {
            "success": True,
            "platform": platform,
            "actor_id": actor_id,
            "run_id": run_id,
            "dataset_id": dataset_id,
            "keyword": keyword,
            "items_count": len(items),
            "raw_file": str(saved_path),
            "items": items,
        }
