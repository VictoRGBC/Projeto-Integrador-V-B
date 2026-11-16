"""
Motor de Inteligência de Mercado e Extração de Insights Estratégicos
para a Integra Engenharia de Sistemas.

Transforma os dados multiplataforma normalizados e classificados em:
1. Ranking de assuntos mais discutidos no mercado
2. Módulos e funcionalidades prioritárias a implementar / evoluir (com Índice de Criticidade e Prioridade - ICP)
3. Dores, gargalos e dificuldades recorrentes relatadas pelos usuários
4. Matriz de correlação Causa-Efeito (Dor Relatada x Funcionalidade Demandada)
5. Diagnóstico comportamental por canal (YouTube vs Instagram vs Reddit)
6. Plano de recomendações práticas para Produto, Implantação e Suporte Técnico
"""

from typing import Any, Dict, List
import pandas as pd


MAPA_RECOMENDACOES_INTEGRA: Dict[str, Dict[str, str]] = {
    "Emissão Fiscal e Tributária (NF-e / CT-e / SPED)": {
        "area": "Produto & Engenharia Fiscal",
        "prioridade": "Alta",
        "acao": (
            "Implementar validação preventiva de regras tributárias (NF-e/NFC-e/NFS-e/CT-e e Reforma Tributária IBS/CBS) "
            "antes do envio à SEFAZ, com alertas claros em linguagem de negócio e importação automatizada de XML."
        ),
    },
    "Integração via API, Webhooks e Marketplaces": {
        "area": "Arquitetura & Integrações",
        "prioridade": "Alta",
        "acao": (
            "Disponibilizar hub de conectores plug-and-play e APIs REST/Webhooks documentadas "
            "para sincronização em tempo real de estoque e pedidos com e-commerces, marketplaces, TEF e bancos."
        ),
    },
    "Gestão Financeira, Contábil e Fluxo de Caixa": {
        "area": "Módulo Financeiro & Contábil",
        "prioridade": "Alta",
        "acao": (
            "Automatizar a conciliação bancária (PIX/Boletos), projeção de fluxo de caixa, DRE gerencial "
            "e integração contábil sem redigitação de lançamentos."
        ),
    },
    "Controle de Estoque, Compras e Logística": {
        "area": "Módulo Suprimentos & Logística",
        "prioridade": "Média-Alta",
        "acao": (
            "Aprimorar o rastreamento de estoque multi-depósito em tempo real, controle de validade/lote, "
            "alertas de ponto de ressuprimento e baixa automática integrada ao faturamento."
        ),
    },
    "Dashboards BI, Relatórios e Indicadores (KPIs)": {
        "area": "Business Intelligence & Analytics",
        "prioridade": "Alta",
        "acao": (
            "Incorporar painéis executivos nativos no ERP com indicadores prontos (DRE, curva ABC, "
            "giro de estoque, ticket médio e margem de contribuição) para decisão Data-Driven."
        ),
    },
    "Automação com IA e Workflows Operacionais": {
        "area": "Inovação & Automação (IA)",
        "prioridade": "Alta",
        "acao": (
            "Introduzir assistentes inteligentes e workflows automatizados para eliminar tarefas repetitivas, "
            "classificar lançamentos, enviar alertas no WhatsApp e detectar anomalias operacionais."
        ),
    },
    "CRM, Gestão Comercial e Frente de Caixa (PDV)": {
        "area": "Módulo Comercial & Vendas",
        "prioridade": "Alta",
        "acao": (
            "Unificar a jornada entre pré-venda (CRM, WhatsApp, Orçamentos e Força de Vendas Mobile) "
            "e pós-venda (PDV ágil e Faturamento), eliminando controles paralelos."
        ),
    },
    "Cloud ERP (Nuvem) e Acesso Mobile": {
        "area": "Infraestrutura & Mobile",
        "prioridade": "Média-Alta",
        "acao": (
            "Expandir recursos de operação 100% Web/Cloud com guarda segura de certificado digital "
            "e aplicativo mobile para aprovações gerenciais e pedidos externos."
        ),
    },
    "Portal de Suporte, Helpdesk e Treinamento Guiado": {
        "area": "Suporte Técnico & Customer Success",
        "prioridade": "Alta",
        "acao": (
            "Criar trilhas de onboarding interativo dentro do sistema (checklists de implantação e vídeos curtos) "
            "e central de ajuda contextual para reduzir o retrabalho e os atrasos de SLA."
        ),
    },
    "Gestão Industrial, PCP, Manufatura e Ordens de Serviço": {
        "area": "Módulo Industrial & Serviços (PCP/OS)",
        "prioridade": "Média-Alta",
        "acao": (
            "Fortalecer o controle de Ordens de Produção (OP/BOM) e Ordens de Serviço (OS) com apontamento "
            "de chão de fábrica e checklists de equipes técnicas em campo."
        ),
    },
}

PAPEL_ESTRATEGICO_CANAL: Dict[str, str] = {
    "YouTube": "Canal de Educação Técnica, Comparação Profunda e Decisão de Implantação",
    "Instagram": "Canal de Vitrine Comercial, Divulgação de Módulos e Captação de Leads PME",
    "Reddit": "Canal de Diagnóstico Crítico, Relatos Técnicos Sem Filtro e Dores de ERPs Legados",
    "LinkedIn": "Canal Corporativo B2B, Decisores Executivos (C-Level/TI) e Governança de ERP",
}


def explodir_campo_multivalorado(
    df: pd.DataFrame,
    coluna: str,
    ignorar_valores: tuple = ("Geral / Institucional", "Sem dor específica relatada", ""),
) -> pd.DataFrame:
    """
    Desmembra campos multivalorados separados por '; ' (como `funcionalidades` e `dores_relatadas`)
    e calcula frequência, percentual, distribuição por sentimento, taxa de atrito (% negativo)
    e Índice de Criticidade e Prioridade (ICP = mencoes + 1.5 * negativos).
    """
    colunas_padrao = [
        "item",
        "mencoes",
        "percentual_registros",
        "positivos",
        "negativos",
        "neutros",
        "taxa_atrito_pct",
        "score_prioridade",
    ]
    if df.empty or coluna not in df.columns:
        return pd.DataFrame(columns=colunas_padrao)

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
        return pd.DataFrame(columns=colunas_padrao)

    df_exp = pd.DataFrame(registros_explodidos)
    agrupado = (
        df_exp.groupby("item", as_index=False)
        .agg(
            mencoes=("sentimento", "count"),
            positivos=("sentimento", lambda s: int((s == "Positivo").sum())),
            negativos=("sentimento", lambda s: int((s == "Negativo").sum())),
            neutros=("sentimento", lambda s: int((s == "Neutro").sum())),
        )
    )
    agrupado["percentual_registros"] = (
        agrupado["mencoes"] * 100.0 / max(total_base, 1)
    ).round(1)
    agrupado["taxa_atrito_pct"] = (
        agrupado["negativos"] * 100.0 / agrupado["mencoes"].clip(lower=1)
    ).round(1)
    agrupado["score_prioridade"] = (
        agrupado["mencoes"] + 1.5 * agrupado["negativos"]
    ).round(1)

    agrupado = agrupado.sort_values(
        ["mencoes", "score_prioridade"], ascending=[False, False]
    ).reset_index(drop=True)
    return agrupado[colunas_padrao]


def gerar_matriz_dor_vs_funcionalidade(df: pd.DataFrame) -> pd.DataFrame:
    """
    Constrói uma matriz de coocorrência (Causa-Efeito) entre as Dores Relatadas no Mercado
    e as Funcionalidades de ERP Demandadas nos mesmos registros.
    Retorna DataFrame com colunas: ['dor', 'funcionalidade', 'ocorrencias'].
    """
    colunas_saida = ["dor", "funcionalidade", "ocorrencias"]
    if df.empty or "dores_relatadas" not in df.columns or "funcionalidades" not in df.columns:
        return pd.DataFrame(columns=colunas_saida)

    ignorar_dores = {"Sem dor específica relatada", ""}
    ignorar_funcs = {"Geral / Institucional", ""}
    pares: List[Dict[str, str]] = []

    for _, row in df.iterrows():
        dores_str = str(row.get("dores_relatadas") or "").strip()
        funcs_str = str(row.get("funcionalidades") or "").strip()
        if not dores_str or not funcs_str:
            continue

        dores = [d.strip() for d in dores_str.split(";") if d.strip() not in ignorar_dores]
        funcs = [f.strip() for f in funcs_str.split(";") if f.strip() not in ignorar_funcs]

        for d in dores:
            for f in funcs:
                pares.append({"dor": d, "funcionalidade": f})

    if not pares:
        return pd.DataFrame(columns=colunas_saida)

    df_pares = pd.DataFrame(pares)
    matriz = (
        df_pares.groupby(["dor", "funcionalidade"], as_index=False)
        .size()
        .rename(columns={"size": "ocorrencias"})
        .sort_values("ocorrencias", ascending=False)
        .reset_index(drop=True)
    )
    return matriz


def gerar_analise_canais(df: pd.DataFrame) -> pd.DataFrame:
    """
    Gera diagnóstico comparativo detalhado por plataforma (YouTube, Instagram, Reddit),
    evidenciando o perfil temático, sentimento, funcionalidade mais buscada e dor dominante em cada rede.
    """
    colunas = [
        "Plataforma",
        "Registros",
        "Participação (%)",
        "% Positivo",
        "% Negativo",
        "Assunto Dominante",
        "Funcionalidade Líder no Canal",
        "Principal Dor Relatada no Canal",
        "Papel Estratégico do Canal",
    ]
    if df.empty:
        return pd.DataFrame(columns=colunas)

    total_geral = len(df)
    linhas: List[Dict[str, Any]] = []

    for plat in ["YouTube", "Instagram", "Reddit", "LinkedIn"]:
        sub = df[df["plataforma"] == plat]
        if sub.empty:
            continue
        qtd = len(sub)
        part_pct = round(qtd * 100.0 / max(total_geral, 1), 1)
        pos_pct = round((sub["sentimento"] == "Positivo").sum() * 100.0 / qtd, 1)
        neg_pct = round((sub["sentimento"] == "Negativo").sum() * 100.0 / qtd, 1)

        assuntos_especificos = sub[sub["assunto"] != "Outros"]["assunto"].value_counts()
        if assuntos_especificos.empty:
            assuntos_especificos = sub["assunto"].value_counts()
        assunto_dom = assuntos_especificos.index[0] if not assuntos_especificos.empty else "Outros"

        df_f = explodir_campo_multivalorado(sub, "funcionalidades")
        func_dom = df_f.iloc[0]["item"] if not df_f.empty else "Geral / Institucional"

        df_d = explodir_campo_multivalorado(sub, "dores_relatadas")
        dor_dom = df_d.iloc[0]["item"] if not df_d.empty else "Sem dor específica relatada"

        linhas.append(
            {
                "Plataforma": plat,
                "Registros": qtd,
                "Participação (%)": f"{part_pct:.1f}%",
                "% Positivo": f"{pos_pct:.1f}%",
                "% Negativo": f"{neg_pct:.1f}%",
                "Assunto Dominante": assunto_dom,
                "Funcionalidade Líder no Canal": func_dom,
                "Principal Dor Relatada no Canal": dor_dom,
                "Papel Estratégico do Canal": PAPEL_ESTRATEGICO_CANAL.get(
                    plat, "Canal de Monitoramento de Mercado"
                ),
            }
        )

    return pd.DataFrame(linhas, columns=colunas)


def gerar_plano_recomendacoes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Gera uma tabela priorizada de recomendações estratégicas para a Integra Engenharia de Sistemas
    cruzando as funcionalidades mais demandadas com o volume de menções, taxa de atrito e ICP.
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
                    "Presença (%)": f"{row['percentual_registros']:.1f}%",
                    "Relatos Críticos (Negativos)": int(row["negativos"]),
                    "Taxa de Atrito (%)": f"{row['taxa_atrito_pct']:.1f}%",
                    "Score Prioridade (ICP)": float(row["score_prioridade"]),
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
            "total_registros": 0,
            "assunto_lider": "Sem dados",
            "assunto_lider_qtd": 0,
            "funcionalidade_lider": "Sem dados",
            "funcionalidade_lider_qtd": 0,
            "dor_lider": "Sem dados",
            "dor_lider_qtd": 0,
            "taxa_positividade": 0.0,
            "taxa_negatividade": 0.0,
            "cobertura_tematica_pct": 0.0,
            "cobertura_funcional_pct": 0.0,
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
    especificos_tema = int((df["assunto"] != "Outros").sum())
    especificos_func = int((df["funcionalidades"] != "Geral / Institucional").sum())

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
        "cobertura_tematica_pct": round(especificos_tema * 100.0 / total, 1),
        "cobertura_funcional_pct": round(especificos_func * 100.0 / total, 1),
    }
