"""
Testes unitários da FASE 6 — Dashboard (Filtros e Resiliência) e Orquestrador CLI.
"""

from datetime import date

from dashboard.app import aplicar_filtros
from main import build_arg_parser, etapa_verificar_configuracoes
from processamento.normalizar_dados import normalizar_registros


def test_dashboard_filtros_funcionam_corretamente():
    """Valida a aplicação de filtros por plataforma, palavra-chave, assunto, sentimento e período."""
    yt = [
        {
            "id": "y_1",
            "title": "ERP excelente para implantação",
            "uploadDate": "2026-04-10T10:00:00Z",
            "_coleta_meta": {"palavra_chave": "Implantação de ERP"},
        }
    ]
    rd = [
        {
            "id": "r_1",
            "title": "Suporte com problema e lentidão",
            "createdAt": "2026-08-20T10:00:00Z",
            "_coleta_meta": {"palavra_chave": "Suporte técnico de sistemas"},
        }
    ]
    df = normalizar_registros(registros_youtube=yt, registros_reddit=rd)

    # Filtro apenas por YouTube (funciona mesmo sem dados de Instagram)
    df_yt = aplicar_filtros(
        df,
        plataformas_sel=["YouTube"],
        palavras_sel=["Implantação de ERP", "Suporte técnico de sistemas"],
        assuntos_sel=df["assunto"].unique().tolist(),
        sentimentos_sel=["Positivo", "Negativo", "Neutro"],
        periodo_sel=(date(2026, 1, 1), date(2026, 12, 31)),
    )
    assert len(df_yt) == 1
    assert df_yt.iloc[0]["plataforma"] == "YouTube"

    # Filtro por sentimento Negativo
    df_neg = aplicar_filtros(
        df,
        plataformas_sel=["YouTube", "Reddit"],
        palavras_sel=["Implantação de ERP", "Suporte técnico de sistemas"],
        assuntos_sel=df["assunto"].unique().tolist(),
        sentimentos_sel=["Negativo"],
    )
    assert len(df_neg) == 1
    assert df_neg.iloc[0]["plataforma"] == "Reddit"


def test_main_arg_parser_flags():
    """Verifica se o main.py suporta todas as flags de execução modular exigidas na Seção 9."""
    parser = build_arg_parser()
    args = parser.parse_args(["--coleta", "--tratamento", "--hdfs", "--hive", "--pipeline"])
    assert args.coleta is True
    assert args.tratamento is True
    assert args.hdfs is True
    assert args.hive is True
    assert args.pipeline is True

    status = etapa_verificar_configuracoes(require_token=False)
    assert status["valid"] is True
