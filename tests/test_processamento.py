"""
Testes unitários obrigatórios da FASE 3 — Normalização, Classificação e Processamento (Seção 12).
Nota: Os dados sintéticos abaixo são utilizados EXCLUSIVAMENTE para testes unitários em memória/diretório
temporário e nunca são gravados nos diretórios de dados reais do projeto.
"""

from pathlib import Path
import tempfile

import pandas as pd

from processamento.classificar_dados import (
    classificar_assunto,
    classificar_sentimento,
    identificar_dores_mercado,
    identificar_funcionalidades,
    identificar_temas,
)
from processamento.gerar_insights import (
    explodir_campo_multivalorado,
    gerar_analise_canais,
    gerar_matriz_dor_vs_funcionalidade,
)
from processamento.normalizar_dados import (
    normalizar_instagram,
    normalizar_linkedin,
    normalizar_reddit,
    normalizar_registros,
    normalizar_youtube,
)
from processamento.tratar_dados import executar_tratamento_completo


def test_1_normalizacao_youtube():
    """1. Testa a normalização de um registro de vídeo e comentário do YouTube."""
    raw_yt = {
        "id": "yt_vid_001",
        "title": "Como funciona a implantação de ERP nas empresas",
        "description": "Explicação prática sobre treinamento e parametrização de sistema excelente.",
        "viewCount": 14500,
        "likeCount": 820,
        "commentCount": 64,
        "uploadDate": "2026-03-15T10:30:00.000Z",
        "url": "https://www.youtube.com/watch?v=yt_vid_001",
        "_coleta_meta": {
            "plataforma": "YouTube",
            "actor_id": "streamers/youtube-scraper",
            "id_execucao": "run_yt_1",
            "palavra_chave": "Implantação de ERP",
            "data_coleta": "2026-11-13T12:00:00Z",
        },
    }
    norm = normalizar_youtube(raw_yt)
    assert norm["plataforma"] == "YouTube"
    assert norm["tipo_registro"] == "publicacao"
    assert norm["id_registro"] == "yt_vid_001"
    assert norm["curtidas"] == 820
    assert norm["comentarios"] == 64
    assert norm["visualizacoes"] == 14500
    assert norm["compartilhamentos"] is None  # YouTube não possui compartilhamentos públicos
    assert norm["data_publicacao"] == "2026-03-15T10:30:00Z"
    assert norm["sentimento"] == "Positivo"
    assert norm["assunto"] == "Implantação"


def test_2_normalizacao_instagram():
    """2. Testa a normalização de uma publicação do Instagram."""
    raw_ig = {
        "id": "ig_post_999",
        "shortCode": "C9abcXYZ",
        "caption": "Nosso suporte técnico resolveu os chamados com SLA rápido e eficiente! @cliente_real",
        "likesCount": 150,
        "commentsCount": 18,
        "timestamp": "2026-05-20T14:15:00.000Z",
        "url": "https://www.instagram.com/p/C9abcXYZ/",
        "_coleta_meta": {
            "plataforma": "Instagram",
            "actor_id": "apify/instagram-scraper",
            "id_execucao": "run_ig_1",
            "palavra_chave": "Suporte técnico de sistemas",
            "data_coleta": "2026-11-13T12:00:00Z",
        },
    }
    norm = normalizar_instagram(raw_ig)
    assert norm["plataforma"] == "Instagram"
    assert norm["tipo_registro"] == "publicacao"
    assert norm["id_registro"] == "ig_post_999"
    assert norm["id_publicacao"] == "C9abcXYZ"
    assert norm["curtidas"] == 150
    assert norm["comentarios"] == 18
    assert norm["visualizacoes"] is None
    assert "@[USUARIO]" in norm["texto"]  # Verifica pseudonimização LGPD
    assert norm["sentimento"] == "Positivo"
    assert norm["assunto"] == "Atendimento e suporte"


def test_3_normalizacao_reddit():
    """3. Testa a normalização de publicação e comentário do Reddit."""
    raw_rd_comment = {
        "id": "t1_rdcomm77",
        "parentId": "t3_rdpost10",
        "dataType": "comment",
        "body": "O sistema trava muito e apresenta lentidão e erro no módulo financeiro.",
        "upVotes": 35,
        "createdAt": "2026-06-10T08:00:00Z",
        "url": "https://www.reddit.com/r/erp/comments/rdpost10/comment/rdcomm77/",
        "_coleta_meta": {
            "plataforma": "Reddit",
            "actor_id": "trudax/reddit-scraper-lite",
            "id_execucao": "run_rd_1",
            "palavra_chave": "Dificuldades com ERP",
            "data_coleta": "2026-11-13T12:00:00Z",
        },
    }
    norm = normalizar_reddit(raw_rd_comment)
    assert norm["plataforma"] == "Reddit"
    assert norm["tipo_registro"] == "comentario"
    assert norm["id_registro"] == "t1_rdcomm77"
    assert norm["id_publicacao"] == "t3_rdpost10"
    assert norm["curtidas"] == 35
    assert norm["sentimento"] == "Negativo"
    assert norm["assunto"] in ("Desempenho e lentidão", "Funcionalidades")


def test_3b_normalizacao_linkedin():
    """3b. Testa a normalização de publicação corporativa do LinkedIn."""
    raw_li = {
        "urn": "urn:li:activity:730999888777",
        "text": "Concluímos com sucesso o go-live da implantação de ERP industrial com integração API e BI!",
        "stats": {
            "total_reactions": 48,
            "comments": 9,
            "reposts": 5,
        },
        "posted_at": {
            "date": "2026-07-12 09:45:00",
            "timestamp": 1783849500000,
        },
        "url": "https://www.linkedin.com/posts/activity-730999888777",
        "_coleta_meta": {
            "plataforma": "LinkedIn",
            "actor_id": "apimaestro/linkedin-posts-search-scraper-no-cookies",
            "id_execucao": "run_li_1",
            "palavra_chave": "Implantação de ERP",
            "data_coleta": "2026-11-13T12:00:00Z",
        },
    }
    norm = normalizar_linkedin(raw_li)
    assert norm["plataforma"] == "LinkedIn"
    assert norm["tipo_registro"] == "publicacao"
    assert norm["id_registro"] == "urn:li:activity:730999888777"
    assert norm["curtidas"] == 48
    assert norm["comentarios"] == 9
    assert norm["compartilhamentos"] == 5
    assert norm["visualizacoes"] is None
    assert norm["sentimento"] == "Positivo"
    assert norm["assunto"] in ("Implantação", "Integração e automação")


def test_4_tratamento_campos_ausentes_sem_inventar_zeros():
    """4. Garante que métricas ausentes permanecem nulas (None/<NA>) e não viram 0."""
    raw_incompleto = {
        "id": "yt_sem_metricas",
        "title": "Discussão geral sobre software corporativo",
    }
    norm = normalizar_youtube(raw_incompleto)
    assert norm["curtidas"] is None
    assert norm["comentarios"] is None
    assert norm["compartilhamentos"] is None
    assert norm["visualizacoes"] is None
    assert norm["data_publicacao"] is None

    df = normalizar_registros(registros_youtube=[raw_incompleto])
    assert pd.isna(df.loc[0, "curtidas"])
    assert pd.isna(df.loc[0, "visualizacoes"])


def test_5_remocao_duplicidades():
    """5. Verifica a remoção de duplicidades por (plataforma, tipo_registro, id_registro)."""
    item_1 = {"id": "dup_01", "title": "Vídeo duplicado sobre ERP"}
    item_2 = {"id": "dup_01", "title": "Vídeo duplicado sobre ERP (cópia)"}
    item_comment = {
        "cid": "dup_01",
        "videoId": "dup_01",
        "comment": "Comentário com mesmo ID mas tipo diferente",
    }

    df = normalizar_registros(registros_youtube=[item_1, item_2, item_comment])
    # item_1 e item_2 têm mesma plataforma='YouTube', tipo_registro='publicacao', id_registro='dup_01'
    # item_comment tem tipo_registro='comentario', logo deve ser preservado
    assert len(df) == 2
    tipos = set(df["tipo_registro"].tolist())
    assert tipos == {"publicacao", "comentario"}


def test_6_classificacao_sentimentos():
    """6. Verifica classificação heurística exploratória de sentimentos (Positivo, Negativo, Neutro)."""
    assert (
        classificar_sentimento("O software é excelente, rápido, fácil e recomendo muito.")
        == "Positivo"
    )
    assert (
        classificar_sentimento("Sistema péssimo, lento, cheio de erro e suporte ruim.")
        == "Negativo"
    )
    assert (
        classificar_sentimento("A empresa anunciou uma atualização na versão 4.2 nesta terça.")
        == "Neutro"
    )


def test_7_classificacao_tematica_e_multiplos_temas():
    """7. Verifica classificação temática nas 7 categorias e suporte a temas adicionais."""
    assert (
        classificar_assunto("O atendimento do suporte demorou para responder o chamado e SLA.")
        == "Atendimento e suporte"
    )
    assert (
        classificar_assunto("A implantação, migração de dados e treinamento da equipe.")
        == "Implantação"
    )
    assert (
        classificar_assunto("A mensalidade e o custo da licença ficaram com preço alto.")
        == "Preço e custo"
    )
    assert (
        classificar_assunto("O módulo de nota fiscal eletrônica e relatório financeiro.")
        == "Funcionalidades"
    )
    assert (
        classificar_assunto("Muita lentidão, sistema pesado e travando toda hora.")
        == "Desempenho e lentidão"
    )
    assert (
        classificar_assunto("Integração via API e webhook para automação de workflow.")
        == "Integração e automação"
    )
    assert classificar_assunto("Bom dia a todos do grupo.") == "Outros"

    # Verifica identificação de mais de um tema no mesmo registro
    principal, adicionais = identificar_temas(
        "A implantação teve problema no treinamento, além de lentidão e suporte ausente."
    )
    assert principal == "Implantação"
    assert "Desempenho e lentidão" in adicionais or "Atendimento e suporte" in adicionais


def test_8_consolidacao_dos_registros_multiplataforma():
    """8. Verifica consolidação multiplataforma e geração do CSV UTF-8-SIG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        yt_dir = base / "youtube"
        ig_dir = base / "instagram"
        rd_dir = base / "reddit"
        li_dir = base / "linkedin"
        yt_dir.mkdir()
        ig_dir.mkdir()
        rd_dir.mkdir()
        li_dir.mkdir()

        (yt_dir / "yt.json").write_text(
            '[{"id": "y1", "title": "ERP excelente para automação via API", "viewCount": 100}]',
            encoding="utf-8",
        )
        (ig_dir / "ig.json").write_text(
            '[{"id": "i1", "shortCode": "sc1", "caption": "Treinamento e implantação de ERP", "likesCount": 25}]',
            encoding="utf-8",
        )
        (rd_dir / "rd.json").write_text(
            '[{"id": "r1", "title": "Dúvida sobre preço e mensalidade de ERP", "upVotes": 12}]',
            encoding="utf-8",
        )
        (li_dir / "li.json").write_text(
            '[{"urn": "l1", "text": "Governança corporativa e implantação de ERP com BI", "stats": {"total_reactions": 40}}]',
            encoding="utf-8",
        )

        out_csv = base / "dados_multiplataforma.csv"
        df = executar_tratamento_completo(
            raw_youtube_dir=yt_dir,
            raw_instagram_dir=ig_dir,
            raw_reddit_dir=rd_dir,
            raw_linkedin_dir=li_dir,
            output_csv_path=out_csv,
        )

        assert len(df) == 4
        assert set(df["plataforma"].tolist()) == {"YouTube", "Instagram", "Reddit", "LinkedIn"}
        assert out_csv.exists()
        # Verifica assinatura UTF-8-SIG (BOM)
        raw_bytes = out_csv.read_bytes()
        assert raw_bytes.startswith(b"\xef\xbb\xbf")


def test_9_termos_hifenizados_e_multilingues():
    """9. Verifica correspondência exata de termos hifenizados (NF-e, CT-e, go-live, pós-venda) e EN."""
    funcs = identificar_funcionalidades("Emissão rápida de NF-e, NFC-e, NFS-e e CT-e no sistema.")
    assert "Emissão Fiscal e Tributária (NF-e / CT-e / SPED)" in funcs

    assunto = classificar_assunto("Planejamento do go-live e pós-venda na empresa.")
    assert assunto in ("Implantação", "Atendimento e suporte")

    sent_en = classificar_sentimento(
        "Why ERP projects fail: poor data migration, scope creep and low user adoption."
    )
    assert sent_en == "Negativo"

    dores_en = identificar_dores_mercado(
        "Struggling with poor data migration, scattered data in Excel and low user adoption."
    )
    assert "Complexidade na Implantação e Parametrização" in dores_en
    assert "Retrabalho Manual e Planilhas Descentralizadas" in dores_en
    assert "Dificuldade de Usabilidade e Falta de Treinamento" in dores_en


def test_10_matriz_dor_vs_funcionalidade_e_analise_canais():
    """10. Verifica geração da matriz Causa-Efeito (Dor x Funcionalidade), Score ICP e análise por canal."""
    yt = [
        {
            "id": "yt_10",
            "title": "Implantação de ERP com erro em planilha Excel e módulo financeiro",
            "viewCount": 500,
        }
    ]
    ig = [
        {
            "id": "ig_10",
            "shortCode": "sc10",
            "caption": "Sistema excelente de vendas PDV e emissão de NF-e sem retrabalho!",
            "likesCount": 30,
        }
    ]
    df = normalizar_registros(registros_youtube=yt, registros_instagram=ig)

    df_exp = explodir_campo_multivalorado(df, "funcionalidades")
    assert "taxa_atrito_pct" in df_exp.columns
    assert "score_prioridade" in df_exp.columns

    df_matriz = gerar_matriz_dor_vs_funcionalidade(df)
    assert not df_matriz.empty
    assert set(df_matriz.columns) == {"dor", "funcionalidade", "ocorrencias"}

    df_canais = gerar_analise_canais(df)
    assert len(df_canais) == 2
    assert "Papel Estratégico do Canal" in df_canais.columns

