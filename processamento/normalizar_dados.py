"""
Módulo de normalização de dados heterogêneos das três plataformas (YouTube, Instagram e Reddit)
para o modelo relacional/analítico unificado (Seção 4).
Inclui extração de comentários aninhados (Instagram/Reddit), filtragem de ruído semântico
e enriquecimento analítico de funcionalidades demandadas e dores de mercado.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from processamento.classificar_dados import (
    classificar_sentimento,
    identificar_dores_mercado,
    identificar_funcionalidades,
    identificar_temas,
)

# Ordem oficial das colunas do modelo unificado + enriquecimento analítico + rastreabilidade
COLUNAS_MODELO_UNIFICADO: List[str] = [
    "plataforma",
    "tipo_registro",
    "id_registro",
    "id_publicacao",
    "texto",
    "data_publicacao",
    "data_coleta",
    "palavra_chave",
    "curtidas",
    "comentarios",
    "compartilhamentos",
    "visualizacoes",
    "url_publicacao",
    "sentimento",
    "assunto",
    "temas_adicionais",
    "funcionalidades",
    "dores_relatadas",
    "id_execucao",
    "actor_id",
    "origem_dado",
    "status_tratamento",
]

COLUNAS_METRICAS_INTEIRAS: List[str] = [
    "curtidas",
    "comentarios",
    "compartilhamentos",
    "visualizacoes",
]

# Subreddits médicos/psicológicos onde a sigla "ERP" significa "Exposure and Response Prevention"
# (terapia para TOC/OCD) ou Roleplay, não tendo relação com sistemas de gestão empresarial.
SUBREDDITS_FORA_DE_ESCOPO = {
    "ocd",
    "rocd",
    "pureo",
    "erptherapy",
    "anxiety",
    "mentalhealth",
    "therapists",
    "vrchat",
    "ffxiv",
    "secondlife",
    "sexualidade",
    "relacionamentos",
    "desabafos",
    "perguntas",
    "uruguay",
    "sweden",
    "autonomoses",
    "literaciafinanceira",
    "iitkgp",
}

TERMOS_FORA_DE_ESCOPO_ERP = (
    "exposure and response prevention",
    "exposure & response prevention",
    "exposure therapy",
    "relationship ocd",
    "mental compulsions",
    "intrusive thoughts",
    "engravidar",
    "disfuncao eretil",
    "disfunção erétil",
    "penetracao",
    "penetração",
    "sexualite",
    "sexualité",
    "erotic roleplay",
    "sergei strelec",
    "hiren's bootcd",
    "apostila ufc",
    "ruidos estranhos e aquecimento",
    "ruídos estranhos e aquecimento",
    "suporte cas informatica",
    "suporte cas informática",
    "atendimento em vargem grande",
    "deu pane? liga pra fj",
    "outlook fora do ar",
    "o outlook caiu",
    "qurilish obyektlarida",
    "banco do brasil anunciou lucro",
    "anthropic, empresa de tecnologia",
    "dividendos acima de r$ 50 mil",
    "calendario trabalhista do ano",
    "calendário trabalhista do ano",
    "trocar de endereco parece simples",
    "trocar de endereço parece simples",
    "primer laburo como ingeniero",
    "me quiero pasar a sistemas",
    "que sistema operativo usas",
    "qué sistema operativo usas",
    "print-on-demand",
    "lidar com a ansiedade neste mercado",
    "i got deported and want 180 my life",
    "quit my 9-5 tech sales job",
    "early revenue, no product yet",
    "where are y’all finding software development clients",
    "where are y'all finding software development clients",
    "madali pa ba makahanap",
    "tell your org we're cooked",
)


def padronizar_nome_plataforma(plataforma: str) -> str:
    """Padroniza o nome da plataforma para 'YouTube', 'Instagram', 'Reddit' ou 'LinkedIn'."""
    if not plataforma:
        return "Desconhecida"
    chave = str(plataforma).strip().lower()
    mapa = {
        "youtube": "YouTube",
        "yt": "YouTube",
        "instagram": "Instagram",
        "ig": "Instagram",
        "reddit": "Reddit",
        "linkedin": "LinkedIn",
        "li": "LinkedIn",
    }
    return mapa.get(chave, str(plataforma).strip())


def converter_data_iso8601(valor: Any) -> Optional[str]:
    """
    Converte strings de data, timestamps Unix ou objetos datetime para o formato
    ISO 8601 UTC padronizado (YYYY-MM-DDTHH:MM:SSZ). Retorna None se ausente ou inválido.
    """
    if valor is None or valor == "":
        return None

    try:
        if isinstance(valor, (int, float)):
            ts = float(valor)
            if ts > 1e11:
                ts = ts / 1000.0
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        texto_data = str(valor).strip()
        if not texto_data:
            return None

        if texto_data.isdigit():
            ts = float(texto_data)
            if ts > 1e11:
                ts = ts / 1000.0
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        dt_parsed = pd.to_datetime(texto_data, utc=True, errors="coerce")
        if pd.isna(dt_parsed):
            return None
        return dt_parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def converter_metrica_inteira(valor: Any) -> Optional[int]:
    """
    Converte métricas numéricas para int quando disponíveis.
    Preserva None (nulo) quando o campo está ausente, vazio ou não se aplica à plataforma,
    evitando substituir nulo por zero indevidamente (Regra 4.2.5 e 4.2.6).
    """
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float):
        if pd.isna(valor):
            return None
        return int(valor)
    if isinstance(valor, str):
        limpo = valor.strip().replace(",", "").replace(".", "")
        if not limpo:
            return None
        if limpo.lstrip("-").isdigit():
            return int(limpo)
    return None


def padronizar_texto(texto: Any) -> Optional[str]:
    """
    Limpa quebras de linha, tabulações, espaços múltiplos e pseudonimiza menções (@usuario)
    ou e-mails expostos para conformidade com a LGPD e compatibilidade com CSV/Hive.
    """
    if texto is None:
        return None
    if isinstance(texto, float) and pd.isna(texto):
        return None
    bruto = str(texto).strip()
    if not bruto:
        return None

    sem_email = re.sub(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL_OMITIDO]", bruto
    )
    sem_handle = re.sub(r"(?<!\w)@[a-zA-Z0-9_.-]{2,30}", "@[USUARIO]", sem_email)

    sem_quebras = re.sub(r"[\r\n\t]+", " ", sem_handle)
    normalizado = re.sub(r"\s{2,}", " ", sem_quebras).strip()
    return normalizado if normalizado else None


def _extrair_meta(
    registro: Dict[str, Any],
    plataforma_padrao: str,
    actor_padrao: str,
    palavra_chave: Optional[str] = None,
    data_coleta: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """Extrai metadados técnicos de auditoria embutidos por _coleta_meta ou argumentos."""
    meta = registro.get("_coleta_meta") if isinstance(registro.get("_coleta_meta"), dict) else {}
    coleta_iso = converter_data_iso8601(
        data_coleta or meta.get("data_coleta") or registro.get("scrapedAt")
    )
    if not coleta_iso:
        coleta_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    kw = (
        palavra_chave
        or meta.get("palavra_chave")
        or registro.get("searchQuery")
        or registro.get("searchTerm")
        or "Não informada"
    )
    actor = meta.get("actor_id") or actor_padrao
    run_id = meta.get("id_execucao") or registro.get("runId") or "local_run"
    origem = meta.get("origem_dado") or f"apify:{actor}"

    return {
        "plataforma": padronizar_nome_plataforma(meta.get("plataforma") or plataforma_padrao),
        "palavra_chave": str(kw).strip(),
        "data_coleta": coleta_iso,
        "id_execucao": str(run_id).strip(),
        "actor_id": str(actor).strip(),
        "origem_dado": str(origem).strip(),
    }


def _finalizar_registro(campos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica classificação de sentimento, assunto principal, temas adicionais,
    funcionalidades demandadas e dores de mercado, garantindo todas as colunas do modelo.
    """
    texto = campos.get("texto") or ""
    sentimento = classificar_sentimento(texto)
    assunto_principal, temas_adicionais = identificar_temas(texto)
    funcionalidades = identificar_funcionalidades(texto)
    dores_relatadas = identificar_dores_mercado(texto)

    campos["sentimento"] = sentimento
    if (
        assunto_principal == "Outros"
        and campos.get("tipo_registro") == "comentario"
        and "erp" in str(campos.get("palavra_chave") or "").lower()
    ):
        assunto_principal = "Funcionalidades"
    campos["assunto"] = assunto_principal
    campos["temas_adicionais"] = temas_adicionais
    campos["funcionalidades"] = funcionalidades
    campos["dores_relatadas"] = dores_relatadas
    campos["status_tratamento"] = "CLASSIFICADO" if texto else "SEM_TEXTO"

    registro_completo: Dict[str, Any] = {}
    for col in COLUNAS_MODELO_UNIFICADO:
        registro_completo[col] = campos.get(col, None)
    return registro_completo


def normalizar_youtube(
    registro: Dict[str, Any],
    palavra_chave: Optional[str] = None,
    data_coleta: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Adaptador de normalização para registros do YouTube (vídeos ou comentários públicos).
    Suporta saída de streamers/youtube-scraper e streamers/youtube-comments-scraper.
    """
    meta = _extrair_meta(
        registro,
        plataforma_padrao="YouTube",
        actor_padrao="streamers/youtube-scraper",
        palavra_chave=palavra_chave,
        data_coleta=data_coleta,
    )

    is_comment = bool(
        registro.get("cid")
        or registro.get("commentId")
        or (registro.get("comment") and not registro.get("title"))
        or str(registro.get("type", "")).lower() == "comment"
    )
    tipo_registro = "comentario" if is_comment else "publicacao"

    if is_comment:
        id_registro = str(
            registro.get("cid")
            or registro.get("commentId")
            or registro.get("id")
            or ""
        ).strip()
        id_publicacao = str(
            registro.get("videoId")
            or registro.get("pageUrl")
            or id_registro
        ).strip()
        texto_bruto = registro.get("comment") or registro.get("text") or ""
        curtidas = converter_metrica_inteira(
            registro.get("voteCount")
            if registro.get("voteCount") is not None
            else registro.get("likes")
        )
        comentarios = converter_metrica_inteira(registro.get("replyCount"))
        visualizacoes = None
    else:
        id_registro = str(
            registro.get("id")
            or registro.get("videoId")
            or ""
        ).strip()
        id_publicacao = id_registro
        titulo = str(registro.get("title") or "").strip()
        descricao = str(registro.get("description") or registro.get("text") or "").strip()
        texto_bruto = (
            f"{titulo}. {descricao}".strip(". ")
            if titulo and descricao
            else (titulo or descricao)
        )
        curtidas = converter_metrica_inteira(
            registro.get("likeCount")
            if registro.get("likeCount") is not None
            else registro.get("likes")
        )
        comentarios = converter_metrica_inteira(
            registro.get("commentCount")
            if registro.get("commentCount") is not None
            else registro.get("commentsCount")
        )
        visualizacoes = converter_metrica_inteira(
            registro.get("viewCount")
            if registro.get("viewCount") is not None
            else registro.get("views")
        )

    compartilhamentos = converter_metrica_inteira(registro.get("shareCount"))

    data_pub = converter_data_iso8601(
        registro.get("uploadDate")
        or registro.get("date")
        or registro.get("publishedAt")
        or registro.get("publishedTimeText")
    )
    url = registro.get("url") or registro.get("pageUrl") or (
        f"https://www.youtube.com/watch?v={id_publicacao}" if id_publicacao else None
    )

    campos = {
        **meta,
        "tipo_registro": tipo_registro,
        "id_registro": id_registro or None,
        "id_publicacao": id_publicacao or None,
        "texto": padronizar_texto(texto_bruto),
        "data_publicacao": data_pub,
        "curtidas": curtidas,
        "comentarios": comentarios,
        "compartilhamentos": compartilhamentos,
        "visualizacoes": visualizacoes,
        "url_publicacao": str(url).strip() if url else None,
    }
    return _finalizar_registro(campos)


def normalizar_instagram(
    registro: Dict[str, Any],
    palavra_chave: Optional[str] = None,
    data_coleta: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Adaptador de normalização para registros do Instagram (publicações ou comentários).
    Suporta saída de apify/instagram-hashtag-scraper e apify/instagram-scraper.
    """
    meta = _extrair_meta(
        registro,
        plataforma_padrao="Instagram",
        actor_padrao="apify/instagram-hashtag-scraper",
        palavra_chave=palavra_chave,
        data_coleta=data_coleta,
    )

    is_comment = bool(
        registro.get("postUrl")
        or (registro.get("text") and not registro.get("caption") and not registro.get("shortCode"))
        or str(registro.get("type", "")).lower() == "comment"
    )
    tipo_registro = "comentario" if is_comment else "publicacao"

    id_registro = str(
        registro.get("id")
        or registro.get("shortCode")
        or ""
    ).strip()

    if is_comment:
        id_publicacao = str(
            registro.get("postId")
            or registro.get("postShortCode")
            or registro.get("postUrl")
            or id_registro
        ).strip()
        texto_bruto = registro.get("text") or registro.get("caption") or ""
        curtidas = converter_metrica_inteira(registro.get("likesCount"))
        comentarios = converter_metrica_inteira(registro.get("repliesCount"))
        visualizacoes = None
    else:
        id_publicacao = str(
            registro.get("shortCode")
            or id_registro
        ).strip()
        texto_bruto = registro.get("caption") or registro.get("text") or ""
        if not texto_bruto and registro.get("hashtags"):
            tags = " ".join(f"#{t}" for t in registro.get("hashtags", []) if t)
            texto_bruto = f"Publicação Instagram {tags}".strip()
        curtidas = converter_metrica_inteira(registro.get("likesCount"))
        comentarios = converter_metrica_inteira(registro.get("commentsCount"))
        visualizacoes = converter_metrica_inteira(
            registro.get("videoViewCount")
            if registro.get("videoViewCount") is not None
            else registro.get("videoPlayCount")
        )

    compartilhamentos = converter_metrica_inteira(registro.get("sharesCount"))
    data_pub = converter_data_iso8601(
        registro.get("timestamp") or registro.get("takenAtTimestamp") or registro.get("createdAt")
    )
    url = registro.get("url") or registro.get("postUrl") or (
        f"https://www.instagram.com/p/{registro.get('shortCode')}/"
        if registro.get("shortCode")
        else None
    )

    campos = {
        **meta,
        "tipo_registro": tipo_registro,
        "id_registro": id_registro or None,
        "id_publicacao": id_publicacao or None,
        "texto": padronizar_texto(texto_bruto),
        "data_publicacao": data_pub,
        "curtidas": curtidas,
        "comentarios": comentarios,
        "compartilhamentos": compartilhamentos,
        "visualizacoes": visualizacoes,
        "url_publicacao": str(url).strip() if url else None,
    }
    return _finalizar_registro(campos)


def normalizar_reddit(
    registro: Dict[str, Any],
    palavra_chave: Optional[str] = None,
    data_coleta: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Adaptador de normalização para registros do Reddit (posts ou comentários).
    Suporta saída de automation-lab/reddit-scraper e trudax/reddit-scraper-lite.
    """
    meta = _extrair_meta(
        registro,
        plataforma_padrao="Reddit",
        actor_padrao="automation-lab/reddit-scraper",
        palavra_chave=palavra_chave,
        data_coleta=data_coleta,
    )

    data_type = str(
        registro.get("dataType") or registro.get("type") or registro.get("kind") or ""
    ).lower()
    is_comment = bool(
        data_type in ("comment", "t1")
        or (registro.get("parentId") and not registro.get("title"))
    )
    tipo_registro = "comentario" if is_comment else "publicacao"

    id_registro = str(
        registro.get("id")
        or registro.get("parsedId")
        or registro.get("post_id")
        or ""
    ).strip()

    if is_comment:
        id_publicacao = str(
            registro.get("postId")
            or registro.get("parentId")
            or id_registro
        ).strip()
        texto_bruto = (
            registro.get("body")
            or registro.get("text")
            or registro.get("selfText")
            or ""
        )
        comentarios = converter_metrica_inteira(
            registro.get("numberOfreplies")
            if registro.get("numberOfreplies") is not None
            else registro.get("numReplies")
        )
    else:
        id_publicacao = id_registro
        titulo = str(registro.get("title") or "").strip()
        corpo = str(
            registro.get("body")
            or registro.get("selfText")
            or registro.get("selftext")
            or registro.get("text")
            or ""
        ).strip()
        texto_bruto = (
            f"{titulo}. {corpo}".strip(". ")
            if titulo and corpo
            else (titulo or corpo)
        )
        comentarios = converter_metrica_inteira(
            registro.get("numberOfComments")
            if registro.get("numberOfComments") is not None
            else (
                registro.get("numComments")
                if registro.get("numComments") is not None
                else registro.get("comment_count")
            )
        )

    curtidas = converter_metrica_inteira(
        registro.get("upVotes")
        if registro.get("upVotes") is not None
        else (
            registro.get("score")
            if registro.get("score") is not None
            else registro.get("ups")
        )
    )
    compartilhamentos = converter_metrica_inteira(registro.get("numCrossposts"))
    visualizacoes = converter_metrica_inteira(registro.get("viewCount"))

    data_pub = converter_data_iso8601(
        registro.get("createdAt")
        or registro.get("created_at")
        or registro.get("created_utc")
    )
    url = registro.get("url") or registro.get("permalink")

    campos = {
        **meta,
        "tipo_registro": tipo_registro,
        "id_registro": id_registro or None,
        "id_publicacao": id_publicacao or None,
        "texto": padronizar_texto(texto_bruto),
        "data_publicacao": data_pub,
        "curtidas": curtidas,
        "comentarios": comentarios,
        "compartilhamentos": compartilhamentos,
        "visualizacoes": visualizacoes,
        "url_publicacao": str(url).strip() if url else None,
    }
    return _finalizar_registro(campos)


def normalizar_linkedin(
    registro: Dict[str, Any],
    palavra_chave: Optional[str] = None,
    data_coleta: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Adaptador de normalização para registros do LinkedIn (publicações ou comentários corporativos B2B).
    Suporta saída de apimaestro/linkedin-posts-search-scraper-no-cookies e harvestapi/linkedin-post-search.
    """
    meta = _extrair_meta(
        registro,
        plataforma_padrao="LinkedIn",
        actor_padrao="apimaestro/linkedin-posts-search-scraper-no-cookies",
        palavra_chave=palavra_chave or registro.get("matchedQuery"),
        data_coleta=data_coleta,
    )

    data_type = str(registro.get("type") or "").lower()
    is_comment = bool(data_type == "comment" or registro.get("commentId"))
    tipo_registro = "comentario" if is_comment else "publicacao"

    id_registro = str(
        registro.get("id")
        or registro.get("urn")
        or registro.get("full_urn")
        or registro.get("activity_id")
        or registro.get("activity_urn")
        or registro.get("postId")
        or ""
    ).strip()

    id_publicacao = str(
        registro.get("postId")
        or registro.get("parentId")
        or id_registro
    ).strip()

    content_field = registro.get("content")
    article_title = ""
    if isinstance(content_field, dict):
        art = content_field.get("article")
        if isinstance(art, dict) and art.get("title"):
            article_title = str(art.get("title")).strip()
        content_str = ""
    else:
        content_str = str(content_field or "").strip()

    texto_principal = str(
        registro.get("text")
        or content_str
        or registro.get("commentary")
        or registro.get("postText")
        or registro.get("title")
        or ""
    ).strip()

    if article_title and article_title.lower() not in texto_principal.lower():
        texto_bruto = (
            f"{article_title}. {texto_principal}".strip(". ")
            if texto_principal
            else article_title
        )
    else:
        texto_bruto = texto_principal

    eng = registro.get("engagement") if isinstance(registro.get("engagement"), dict) else {}
    stats = registro.get("stats") if isinstance(registro.get("stats"), dict) else {}

    curtidas = converter_metrica_inteira(
        eng.get("reactionsCount")
        if eng.get("reactionsCount") is not None
        else (
            eng.get("likes")
            if eng.get("likes") is not None
            else (
                stats.get("total_reactions")
                if stats.get("total_reactions") is not None
                else (
                    stats.get("like")
                    if stats.get("like") is not None
                    else (
                        registro.get("reactionsCount")
                        if registro.get("reactionsCount") is not None
                        else (
                            registro.get("numLikes")
                            if registro.get("numLikes") is not None
                            else registro.get("totalReactionCount")
                        )
                    )
                )
            )
        )
    )

    comentarios = converter_metrica_inteira(
        eng.get("commentsCount")
        if eng.get("commentsCount") is not None
        else (
            stats.get("comments")
            if stats.get("comments") is not None
            else (
                registro.get("commentsCount")
                if registro.get("commentsCount") is not None
                else (
                    registro.get("numComments")
                    if registro.get("numComments") is not None
                    else registro.get("totalCommentCount")
                )
            )
        )
    )

    compartilhamentos = converter_metrica_inteira(
        eng.get("repostsCount")
        if eng.get("repostsCount") is not None
        else (
            stats.get("reposts")
            if stats.get("reposts") is not None
            else (
                stats.get("shares")
                if stats.get("shares") is not None
                else (
                    registro.get("repostsCount")
                    if registro.get("repostsCount") is not None
                    else (
                        registro.get("numShares")
                        if registro.get("numShares") is not None
                        else registro.get("sharesCount")
                    )
                )
            )
        )
    )

    visualizacoes = converter_metrica_inteira(
        eng.get("impressionsCount")
        if eng.get("impressionsCount") is not None
        else (
            registro.get("impressionsCount")
            if registro.get("impressionsCount") is not None
            else registro.get("viewsCount")
        )
    )

    posted_raw = (
        registro.get("postedAt")
        or registro.get("posted_at")
        or registro.get("createdAt")
        or registro.get("publishedAt")
    )
    if isinstance(posted_raw, dict):
        posted_val = (
            posted_raw.get("date")
            or posted_raw.get("timestamp")
            or posted_raw.get("datetime")
        )
    else:
        posted_val = posted_raw
    data_pub = converter_data_iso8601(posted_val)

    url = (
        registro.get("linkedinUrl")
        or registro.get("post_url")
        or registro.get("url")
        or registro.get("postUrl")
        or registro.get("shareUrl")
    )

    campos = {
        **meta,
        "tipo_registro": tipo_registro,
        "id_registro": id_registro or None,
        "id_publicacao": id_publicacao or None,
        "texto": padronizar_texto(texto_bruto),
        "data_publicacao": data_pub,
        "curtidas": curtidas,
        "comentarios": comentarios,
        "compartilhamentos": compartilhamentos,
        "visualizacoes": visualizacoes,
        "url_publicacao": str(url).strip() if url else None,
    }
    return _finalizar_registro(campos)


def _eh_registro_fora_de_escopo(item: Dict[str, Any]) -> bool:
    """
    Filtra publicações originadas em comunidades ou tópicos fora do escopo de software
    de gestão empresarial (ex: terapia 'Exposure and Response Prevention' para TOC/OCD,
    tópicos médicos ou roleplay).
    """
    sub = str(
        item.get("subreddit")
        or item.get("communityName")
        or item.get("parsedCommunityName")
        or ""
    ).strip().lower().lstrip("r/")
    if sub in SUBREDDITS_FORA_DE_ESCOPO:
        return True

    texto_combinado = " ".join(
        str(item.get(k) or "")
        for k in ("title", "description", "text", "body", "selfText", "caption", "content", "commentary")
    ).lower()
    for termo in TERMOS_FORA_DE_ESCOPO_ERP:
        if termo in texto_combinado:
            return True
    return False


def normalizar_registros(
    registros_youtube: Optional[Iterable[Dict[str, Any]]] = None,
    registros_instagram: Optional[Iterable[Dict[str, Any]]] = None,
    registros_reddit: Optional[Iterable[Dict[str, Any]]] = None,
    registros_linkedin: Optional[Iterable[Dict[str, Any]]] = None,
) -> pd.DataFrame:
    """
    Consolida os resultados das quatro plataformas em um único DataFrame padronizado,
    extraindo também comentários públicos aninhados, aplicando tipagem correta de métricas
    inteiras nulas (Int64) e removendo duplicidades com base em (plataforma, tipo_registro, id_registro).
    """
    linhas_normalizadas: List[Dict[str, Any]] = []

    if registros_youtube:
        for item in registros_youtube:
            if isinstance(item, dict) and not _eh_registro_fora_de_escopo(item):
                linhas_normalizadas.append(normalizar_youtube(item))

    if registros_instagram:
        for item in registros_instagram:
            if not isinstance(item, dict) or _eh_registro_fora_de_escopo(item):
                continue
            linhas_normalizadas.append(normalizar_instagram(item))

            # Extrai comentários públicos aninhados retornados em `latestComments`
            latest_comments = item.get("latestComments")
            if isinstance(latest_comments, list):
                parent_code = item.get("shortCode") or item.get("id")
                parent_url = item.get("url")
                parent_meta = item.get("_coleta_meta")
                for idx_c, comm in enumerate(latest_comments):
                    if isinstance(comm, dict) and comm.get("text"):
                        comm_enriquecido = {
                            **comm,
                            "type": "comment",
                            "id": comm.get("id") or f"{parent_code}_c{idx_c + 1}",
                            "postShortCode": parent_code,
                            "postUrl": parent_url,
                            "_coleta_meta": parent_meta,
                        }
                        linhas_normalizadas.append(normalizar_instagram(comm_enriquecido))

    if registros_reddit:
        for item in registros_reddit:
            if not isinstance(item, dict):
                continue
            if _eh_registro_fora_de_escopo(item):
                continue
            linhas_normalizadas.append(normalizar_reddit(item))

            # Extrai comentários públicos aninhados caso presentes na chave `comments`
            nested_comments = item.get("comments")
            if isinstance(nested_comments, list):
                parent_id = item.get("id")
                parent_url = item.get("url")
                parent_meta = item.get("_coleta_meta")
                for idx_c, comm in enumerate(nested_comments):
                    if isinstance(comm, dict) and (comm.get("body") or comm.get("text")):
                        comm_enriquecido = {
                            **comm,
                            "type": "comment",
                            "id": comm.get("id") or f"{parent_id}_rc{idx_c + 1}",
                            "parentId": parent_id,
                            "url": comm.get("url") or parent_url,
                            "_coleta_meta": parent_meta,
                        }
                        linhas_normalizadas.append(normalizar_reddit(comm_enriquecido))

    if registros_linkedin:
        for item in registros_linkedin:
            if not isinstance(item, dict) or _eh_registro_fora_de_escopo(item):
                continue
            linhas_normalizadas.append(normalizar_linkedin(item))

            nested_li_comments = item.get("comments")
            if isinstance(nested_li_comments, list):
                parent_id = item.get("id") or item.get("urn")
                parent_url = item.get("linkedinUrl") or item.get("url") or item.get("post_url")
                parent_meta = item.get("_coleta_meta")
                for idx_c, comm in enumerate(nested_li_comments):
                    if isinstance(comm, dict) and (comm.get("text") or comm.get("content")):
                        comm_enriquecido = {
                            **comm,
                            "type": "comment",
                            "id": comm.get("id") or f"{parent_id}_lic{idx_c + 1}",
                            "postId": parent_id,
                            "linkedinUrl": comm.get("linkedinUrl") or parent_url,
                            "_coleta_meta": parent_meta,
                        }
                        linhas_normalizadas.append(normalizar_linkedin(comm_enriquecido))

    if not linhas_normalizadas:
        df_vazio = pd.DataFrame(columns=COLUNAS_MODELO_UNIFICADO)
        for col in COLUNAS_METRICAS_INTEIRAS:
            df_vazio[col] = df_vazio[col].astype("Int64")
        return df_vazio

    df = pd.DataFrame(linhas_normalizadas, columns=COLUNAS_MODELO_UNIFICADO)

    df = df.dropna(subset=["plataforma", "tipo_registro", "id_registro", "texto"]).copy()

    df = df.drop_duplicates(
        subset=["plataforma", "tipo_registro", "id_registro"], keep="first"
    ).reset_index(drop=True)

    # Remove republicações idênticas (mesmo texto na mesma plataforma e mesmo tipo de registro)
    df = df.drop_duplicates(
        subset=["plataforma", "tipo_registro", "texto"], keep="first"
    ).reset_index(drop=True)

    for col in COLUNAS_METRICAS_INTEIRAS:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    return df
