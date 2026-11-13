"""
Motor de Inteligência de Mercado e Extração de Insights Estratégicos
para a Integra Engenharia de Sistemas.

Transforma os dados multiplataforma normalizados e classificados em:
1. Ranking de assuntos mais discutidos no mercado
2. Módulos e funcionalidades prioritárias a implementar / evoluir
3. Dores, gargalos e dificuldades recorrentes relatadas pelos usuários
4. Plano de recomendações práticas para Produto, Implantação e Suporte Técnico
"""

from typing import Any, Dict, List
import pandas as pd


MAPA_RECOMENDACOES_INTEGRA: Dict[str, Dict[str, str]] = {
    "Emissão Fiscal e Tributária (NF-e / CT-e / SPED)": {
        "area": "Produto & Engenharia Fiscal",
        "prioridade": "Alta",
        "acao": (
            "Implementar validação preventiva de regras tributárias (NF-e/NFC-e/CT-e) antes do envio "
            "à SEFAZ, com alertas claros em linguagem de negócio e atualização automática de alíquotas."
        ),
    },
    "Integração via API, Webhooks e Marketplaces": {
        "area": "Arquitetura & Integrações",
        "prioridade": "Alta",
        "acao": (
            "Disponibilizar hub de conectores plug-and-play e APIs REST/Webhooks bem documentadas "
            "para sincronização automática com e-commerces, marketplaces, CRM e bancos."
        ),
    },
    "Gestão Financeira, Contábil e Fluxo de Caixa": {
        "area": "Módulo Financeiro & Contábil",
        "prioridade": "Alta",
        "acao": (
            "Automatizar a conciliação bancária (PIX/Boletos), projeção de fluxo de caixa em tempo real "
            "e integração contábil sem redigitação de lançamentos."
        ),
    },
    "Controle de Estoque, Compras e Logística": {
        "area": "Módulo Suprimentos & Logística",
        "prioridade": "Média-Alta",
        "acao": (
            "Aprimorar o rastreamento de estoque multi-depósito em tempo real, alertas de ponto de "
            "ressuprimento e integração entre compras, faturamento e expedição."
        ),
    },
    "Dashboards BI, Relatórios e Indicadores (KPIs)": {
        "area": "Business Intelligence & Analytics",
        "prioridade": "Alta",
        "acao": (
            "Incorporar painéis executivos nativos no ERP com indicadores prontos (DRE gerencial, "
            "curva ABC, giro de estoque e margem de contribuição) para decisão Data-Driven."
        ),
    },
    "Automação com IA e Workflows Operacionais": {
        "area": "Inovação & Automação (IA)",
        "prioridade": "Média-Alta",
        "acao": (
            "Introduzir assistentes inteligentes para preenchimento automático de cadastros, "
            "classificação de lançamentos e alertas de anomalias operacionais."
        ),
    },
    "CRM, Gestão Comercial e Frente de Caixa (PDV)": {
        "area": "Módulo Comercial & Vendas",
        "prioridade": "Média",
        "acao": (
            "Unificar a jornada entre pré-venda (CRM/Orçamentos) e pós-venda (Faturamento/ERP), "
            "eliminando perda de histórico de negociações."
        ),
    },
    "Cloud ERP (Nuvem) e Acesso Mobile": {
        "area": "Infraestrutura & Mobile",
        "prioridade": "Média",
        "acao": (
            "Expandir recursos de aprovação gerencial e consulta de indicadores via dispositivo móvel "
            "e navegador com alta disponibilidade."
        ),
    },
    "Portal de Suporte, Helpdesk e Treinamento Guiado": {
        "area": "Suporte Técnico & Customer Success",
        "prioridade": "Alta",
        "acao": (
            "Criar trilhas de onboarding interativo dentro do sistema (tooltips/vídeos curtos por tela) "
            "e autoatendimento integrado para reduzir chamados repetitivos de suporte."
        ),
    },
}


def explodir_campo_multivalorado(
    df: pd.DataFrame,
    coluna: str,
    ignorar_valores: tuple = ("Geral / Institucional", "Sem dor específica relatada", ""),
) -> pd.DataFrame:
    """
    Desmembra campos multivalorados separados por '; ' (como `funcionalidades` e `dores_relatadas`)
    e calcula frequência, percentual e distribuição por sentimento e plataforma.
    """
    if df.empty or coluna not in df.columns:
        return pd.DataFrame(
            columns=["item", "mencoes", "percentual_registros", "positivos", "negativos", "neutros"]
        )

    registros_explodidos: List[Dict[str, Any]] = []
    total_base = len(df)

    for _, row in df.iterrows():
        bruto = str(row.get(coluna) or "").strip()
        if not bruto:
            continue
        partes = [p.strip() for p in bruto.split(";") if p.strip()]
        for parte in partes:
            if parte in ignorar_valores:
                continue
            registros_explodidos.append(
                {
                    "item": parte,
                    "plataforma": row.get("plataforma", ""),
                    "sentimento": row.get("sentimento", "Neutro"),
                }
            )

    if not registros_explodidos:
        return pd.DataFrame(
            columns=["item", "mencoes", "percentual_registros", "positivos", "negativos", "neutros"]
        )

    df_exp = pd.DataFrame(registros_explodidos)
    agrupado = (
        df_exp.groupby("item", as_index=False)
        .agg(
            mencoes=("sentimento", "count"),
            positivos=("sentimento", lambda s: int((s == "Positivo").sum())),
            negativos=("sentimento", lambda s: int((s == "Negativo").sum())),
            neutros=("sentimento", lambda s: int((s == "Neutro").sum())),
        )
        .sort_values("mencoes", ascending=False)
        .reset_index(drop=True)
    )
    agrupado["percentual_registros"] = (agrupado["mencoes"] * 100.0 / max(total_base, 1)).round(1)
    return agrupado


def gerar_plano_recomendacoes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Gera uma tabela priorizada de recomendações estratégicas para a Integra Engenharia de Sistemas
    cruzando as funcionalidades mais demandadas com o volume de menções reais no dataset.
    """
    df_func = explodir_campo_multivalorado(df, "funcionalidades")
    linhas_rec: List[Dict[str, Any]] = []

    if not df_func.empty:
        for _, row in df_func.iterrows():
            nome_func = row["item"]
            info = MAPA_RECOMENDACOES_INTEGRA.get(
                nome_func,
                {
                    "area": "Evolução de Produto",
                    "prioridade": "Média",
                    "acao": "Avaliar demanda recorrente identificada nas discussões públicas do setor.",
                },
            )
            linhas_rec.append(
                {
                    "Funcionalidade / Demanda de Mercado": nome_func,
                    "Menções na Amostra": int(row["mencoes"]),
                    "Participação (%)": f"{row['percentual_registros']:.1f}%",
                    "Relatos Críticos (Negativos)": int(row["negativos"]),
                    "Área Recomendada (Integra)": info["area"],
                    "Prioridade Sugerida": info["prioridade"],
                    "Ação / Implementação Recomendada": info["acao"],
                }
            )

    return pd.DataFrame(linhas_rec)


def gerar_sintese_executiva(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Produz um dicionário com os principais destaques executivos para exibição no Dashboard
    e nos relatórios do projeto.
    """
    if df.empty:
        return {
            "assunto_lider": "Sem dados",
            "funcionalidade_lider": "Sem dados",
            "dor_lider": "Sem dados",
            "taxa_positividade": 0.0,
            "taxa_negatividade": 0.0,
        }

    total = len(df)
    cont_assunto = df[df["assunto"] != "Outros"]["assunto"].value_counts()
    if cont_assunto.empty:
        cont_assunto = df["assunto"].value_counts()
    assunto_lider = cont_assunto.index[0] if not cont_assunto.empty else "Outros"

    df_func = explodir_campo_multivalorado(df, "funcionalidades")
    func_lider = df_func.iloc[0]["item"] if not df_func.empty else "Geral / Institucional"

    df_dores = explodir_campo_multivalorado(df, "dores_relatadas")
    dor_lider = (
        df_dores.iloc[0]["item"] if not df_dores.empty else "Sem dor específica relatada"
    )

    pos = int((df["sentimento"] == "Positivo").sum())
    neg = int((df["sentimento"] == "Negativo").sum())

    return {
        "total_registros": total,
        "assunto_lider": assunto_lider,
        "assunto_lider_qtd": int(cont_assunto.iloc[0]) if not cont_assunto.empty else 0,
        "funcionalidade_lider": func_lider,
        "funcionalidade_lider_qtd": int(df_func.iloc[0]["mencoes"]) if not df_func.empty else 0,
        "dor_lider": dor_lider,
        "dor_lider_qtd": int(df_dores.iloc[0]["mencoes"]) if not df_dores.empty else 0,
        "taxa_positividade": round(pos * 100.0 / total, 1),
        "taxa_negatividade": round(neg * 100.0 / total, 1),
    }
