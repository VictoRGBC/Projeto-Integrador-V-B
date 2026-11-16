"""
Dashboard Executivo de Inteligência de Mercado Multiplataforma — Integra Engenharia de Sistemas.
Desenvolvido com Streamlit e Plotly (Seção 8).
Inclui análise aprofundada de assuntos mais falados, funcionalidades a implementar (com Score ICP),
dores operacionais do mercado, matriz Causa-Efeito (Dor x Funcionalidade), diagnóstico por canal
e matriz de recomendações para a Integra.
"""

from pathlib import Path
import sys
from typing import Optional, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import HIVE_DIR, PROCESSED_CSV_PATH
from hadoop.scripts.enviar_hdfs import executar_fluxo_hdfs
from hive.executar_hive import (
    HIVE_RESULTS_DIR,
    executar_fluxo_hive,
    verificar_hive_disponivel,
)
from processamento.gerar_insights import (
    explodir_campo_multivalorado,
    gerar_analise_canais,
    gerar_matriz_dor_vs_funcionalidade,
    gerar_plano_recomendacoes,
    gerar_sintese_executiva,
)
from processamento.tratar_dados import carregar_dados_tratados, executar_tratamento_completo

CORES_SENTIMENTO = {
    "Positivo": "#10B981",
    "Negativo": "#EF4444",
    "Neutro": "#64748B",
}

CORES_PLATAFORMA = {
    "YouTube": "#FF0000",
    "Instagram": "#E1306C",
    "Reddit": "#FF4500",
    "LinkedIn": "#0A66C2",
}


def carregar_fonte_dados(csv_path: Path = PROCESSED_CSV_PATH) -> Tuple[pd.DataFrame, str]:
    """
    Carrega os dados reais do projeto priorizando os resultados consolidados para o Hive / CSV tratado.
    Retorna (DataFrame, descricao_origem). Nunca gera dados fictícios.
    """
    hive_json = HIVE_RESULTS_DIR / "resumo_consultas_hive.json"
    hive_ativo = verificar_hive_disponivel()

    df = carregar_dados_tratados(csv_path)
    if df.empty:
        return df, "Nenhum dado coletado disponível"

    if hive_ativo or hive_json.exists():
        origem = "Apache Hive / HDFS (/projeto_integrador/dados_tratados/multiplataforma)"
    else:
        origem = f"Dataset Consolidado Multiplataforma ({csv_path.name})"

    return df, origem


def aplicar_filtros(
    df: pd.DataFrame,
    plataformas_sel: list,
    palavras_sel: list,
    assuntos_sel: list,
    sentimentos_sel: list,
    periodo_sel: Optional[Tuple] = None,
) -> pd.DataFrame:
    """Aplica os filtros selecionados pelo usuário de forma segura sobre o DataFrame."""
    if df.empty:
        return df

    filtrado = df.copy()
    if plataformas_sel:
        filtrado = filtrado[filtrado["plataforma"].isin(plataformas_sel)]
    if palavras_sel:
        filtrado = filtrado[filtrado["palavra_chave"].isin(palavras_sel)]
    if assuntos_sel:
        filtrado = filtrado[filtrado["assunto"].isin(assuntos_sel)]
    if sentimentos_sel:
        filtrado = filtrado[filtrado["sentimento"].isin(sentimentos_sel)]

    if periodo_sel and len(periodo_sel) == 2:
        dt_inicio, dt_fim = periodo_sel
        datas_dt = pd.to_datetime(filtrado["data_publicacao"], utc=True, errors="coerce").dt.date
        mask_data = datas_dt.isna() | ((datas_dt >= dt_inicio) & (datas_dt <= dt_fim))
        filtrado = filtrado[mask_data]

    return filtrado.reset_index(drop=True)


def renderizar_dashboard() -> None:
    """Renderiza a interface completa do dashboard Streamlit em três abas."""
    st.set_page_config(
        page_title="Inteligência de Mercado | Integra Engenharia de Sistemas",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #0F172A 0%, #1E293B 100%);
                    padding: 1.4rem 1.8rem; border-radius: 10px; color: #F8FAFC; margin-bottom: 1.2rem;
                    border-left: 6px solid #3B82F6;">
            <h2 style="margin: 0; font-size: 1.65rem; font-weight: 700;">
                Sistema Multiplataforma de Inteligência de Mercado
            </h2>
            <p style="margin: 0.35rem 0 0 0; color: #94A3B8; font-size: 0.95rem;">
                <strong>Integra Engenharia de Sistemas</strong> &bull; PUC Goiás &bull; Projeto Integrador V – B
                (YouTube, Instagram, Reddit &amp; LinkedIn &rarr; Apify &rarr; Hadoop/HDFS &rarr; Apache Hive)
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_bruto, fonte_ativa = carregar_fonte_dados()

    with st.sidebar:
        st.header("⚙️ Controle e Filtros")
        if st.button("🔄 Atualizar Tratamento, HDFS e Hive", use_container_width=True):
            with st.spinner("Reprocessando dados brutos, atualizando HDFS e consultas HiveQL..."):
                df_novo = executar_tratamento_completo()
                if not df_novo.empty:
                    executar_fluxo_hdfs()
                    executar_fluxo_hive()
            st.rerun()

        st.caption(f"**Fonte ativa:** {fonte_ativa}")

        if df_bruto.empty:
            st.warning(
                "Nenhum dataset tratado foi encontrado em `dados/tratados/dados_multiplataforma.csv`."
            )
            st.markdown(
                """
                **Como carregar dados reais:**
                1. Configure seu `APIFY_API_TOKEN` no arquivo `.env`.
                2. Execute a coleta e o tratamento:
                   ```bash
                   python main.py --pipeline
                   ```
                3. Clique em **Atualizar Tratamento, HDFS e Hive** acima.
                """
            )
            st.stop()

        opcoes_plat = sorted(df_bruto["plataforma"].dropna().unique().tolist())
        plataformas_sel = st.multiselect(
            "Plataforma", options=opcoes_plat, default=opcoes_plat
        )

        opcoes_kw = sorted(df_bruto["palavra_chave"].dropna().unique().tolist())
        palavras_sel = st.multiselect(
            "Palavra-chave", options=opcoes_kw, default=opcoes_kw
        )

        opcoes_assunto = sorted(df_bruto["assunto"].dropna().unique().tolist())
        assuntos_sel = st.multiselect(
            "Assunto / Tema", options=opcoes_assunto, default=opcoes_assunto
        )

        opcoes_sent = sorted(df_bruto["sentimento"].dropna().unique().tolist())
        sentimentos_sel = st.multiselect(
            "Sentimento (Heurístico)", options=opcoes_sent, default=opcoes_sent
        )

        datas_validas = pd.to_datetime(
            df_bruto["data_publicacao"], utc=True, errors="coerce"
        ).dropna()
        periodo_sel = None
        if not datas_validas.empty:
            min_date = datas_validas.min().date()
            max_date = datas_validas.max().date()
            if min_date <= max_date:
                periodo_escolhido = st.date_input(
                    "Período de Publicação",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                )
                if isinstance(periodo_escolhido, tuple) and len(periodo_escolhido) == 2:
                    periodo_sel = periodo_escolhido

        st.divider()
        st.info(
            "ℹ️ **Nota Metodológica:** A classificação de sentimentos, assuntos, funcionalidades e dores "
            "utiliza **heurística exploratória multilíngue (PT/EN/ES) baseada em léxico de domínio e expressões contextuais**. "
            "Os dados representam uma amostra pública exploratória do mercado de sistemas "
            "de gestão (ERP) e não constituem opinião direta sobre a Integra Engenharia de Sistemas."
        )

    df = aplicar_filtros(
        df_bruto,
        plataformas_sel=plataformas_sel,
        palavras_sel=palavras_sel,
        assuntos_sel=assuntos_sel,
        sentimentos_sel=sentimentos_sel,
        periodo_sel=periodo_sel,
    )

    if df.empty:
        st.warning("Nenhum registro corresponde aos filtros selecionados na barra lateral.")
        st.stop()

    sintese = gerar_sintese_executiva(df)

    aba1, aba2, aba3 = st.tabs(
        [
            "📈 ABA 1 — Visão Geral e Diagnóstico por Canal",
            "🎯 ABA 2 — Inteligência de Mercado, Funcionalidades e Recomendações",
            "📋 ABA 3 — Auditoria de Dados e Consultas HiveQL",
        ]
    )

    # =========================================================================
    # ABA 1 — VISÃO GERAL E DIAGNÓSTICO POR CANAL
    # =========================================================================
    with aba1:
        total_registros = len(df)
        total_plataformas = df["plataforma"].nunique()
        qtd_publicacoes = int((df["tipo_registro"] == "publicacao").sum())
        qtd_comentarios = int((df["tipo_registro"] == "comentario").sum())
        qtd_positivos = int((df["sentimento"] == "Positivo").sum())
        qtd_negativos = int((df["sentimento"] == "Negativo").sum())

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total de Registros", f"{total_registros:,}".replace(",", "."))
        c2.metric("Plataformas Analisadas", f"{total_plataformas}")
        c3.metric("Publicações", f"{qtd_publicacoes:,}".replace(",", "."))
        c4.metric("Comentários", f"{qtd_comentarios:,}".replace(",", "."))
        c5.metric(
            "Registros Positivos",
            f"{qtd_positivos:,}".replace(",", "."),
            f"{sintese['taxa_positividade']}%",
        )
        c6.metric(
            "Registros Negativos",
            f"{qtd_negativos:,}".replace(",", "."),
            f"-{sintese['taxa_negatividade']}%",
            delta_color="inverse",
        )

        # Destaques Executivos Rápidos
        st.markdown("#### 💡 Destaques Executivos Extraídos da Amostra")
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.success(
                f"**Assunto Mais Falado:**\n\n{sintese['assunto_lider']} "
                f"({sintese['assunto_lider_qtd']} registros)"
            )
        with d2:
            st.info(
                f"**Funcionalidade Mais Demandada:**\n\n{sintese['funcionalidade_lider']} "
                f"({sintese['funcionalidade_lider_qtd']} menções)"
            )
        with d3:
            st.warning(
                f"**Principal Dor / Gargalo Identificado:**\n\n{sintese['dor_lider']} "
                f"({sintese['dor_lider_qtd']} menções)"
            )
        with d4:
            st.info(
                f"**Cobertura Analítica Específica:**\n\n"
                f"Temas: **{sintese['cobertura_tematica_pct']}%** | "
                f"Módulos ERP: **{sintese['cobertura_funcional_pct']}%**"
            )

        st.divider()

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            df_plat = (
                df.groupby(["plataforma", "tipo_registro"], as_index=False)
                .size()
                .rename(columns={"size": "quantidade"})
            )
            fig_plat = px.bar(
                df_plat,
                x="plataforma",
                y="quantidade",
                color="tipo_registro",
                barmode="group",
                title="Distribuição de Registros por Plataforma e Tipo",
                labels={
                    "plataforma": "Plataforma",
                    "quantidade": "Quantidade de Registros",
                    "tipo_registro": "Tipo de Registro",
                },
                text_auto=True,
                color_discrete_sequence=["#2563EB", "#93C5FD"],
            )
            fig_plat.update_layout(height=380)
            st.plotly_chart(fig_plat, use_container_width=True)

        with col_g2:
            df_sent = (
                df.groupby("sentimento", as_index=False)
                .size()
                .rename(columns={"size": "quantidade"})
            )
            fig_sent = px.pie(
                df_sent,
                names="sentimento",
                values="quantidade",
                hole=0.45,
                title="Distribuição de Sentimentos (Classificação Heurística Exploratória)",
                color="sentimento",
                color_discrete_map=CORES_SENTIMENTO,
            )
            fig_sent.update_traces(textinfo="percent+label+value")
            fig_sent.update_layout(height=380)
            st.plotly_chart(fig_sent, use_container_width=True)

        df_kw = (
            df.groupby(["palavra_chave", "sentimento"], as_index=False)
            .size()
            .rename(columns={"size": "quantidade"})
        )
        fig_kw = px.bar(
            df_kw,
            x="quantidade",
            y="palavra_chave",
            color="sentimento",
            orientation="h",
            title="Volume de Registros por Palavra-Chave e Sentimento",
            labels={
                "quantidade": "Total de Registros",
                "palavra_chave": "Palavra-Chave Pesquisada",
                "sentimento": "Sentimento",
            },
            color_discrete_map=CORES_SENTIMENTO,
            text_auto=True,
        )
        fig_kw.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_kw, use_container_width=True)

        st.divider()
        st.markdown("#### 🌐 Diagnóstico Comportamental e Estratégico por Canal")
        st.caption(
            "Síntese comparativa do comportamento temático, polaridade, demandas de produto e dores predominantes em cada mídia social."
        )
        df_canais = gerar_analise_canais(df)
        if not df_canais.empty:
            st.dataframe(df_canais, use_container_width=True, hide_index=True)

    # =========================================================================
    # ABA 2 — ANÁLISE DE MERCADO, FUNCIONALIDADES E RECOMENDAÇÕES
    # =========================================================================
    with aba2:
        st.subheader("1. Assuntos Mais Falados e Dificuldades Relatadas no Mercado")
        col_m1, col_m2 = st.columns(2)

        with col_m1:
            df_temas = (
                df.groupby(["assunto", "sentimento"], as_index=False)
                .size()
                .rename(columns={"size": "quantidade"})
            )
            fig_temas = px.bar(
                df_temas,
                x="quantidade",
                y="assunto",
                color="sentimento",
                orientation="h",
                title="Assuntos Mais Recorrentes por Sentimento",
                labels={
                    "quantidade": "Registros",
                    "assunto": "Assunto Principal",
                    "sentimento": "Sentimento",
                },
                color_discrete_map=CORES_SENTIMENTO,
                text_auto=True,
            )
            fig_temas.update_layout(height=420, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_temas, use_container_width=True)

        with col_m2:
            df_dores = explodir_campo_multivalorado(df, "dores_relatadas")
            if not df_dores.empty:
                df_dores_plot = df_dores.sort_values("mencoes", ascending=True)
                fig_dif = px.bar(
                    df_dores_plot,
                    x="mencoes",
                    y="item",
                    orientation="h",
                    title="Principais Dores e Gargalos Operacionais Relatados pelos Usuários",
                    labels={
                        "mencoes": "Menções nos Registros",
                        "item": "Dor / Gargalo Identificado",
                        "taxa_atrito_pct": "Taxa de Atrito (% Negativo)",
                        "score_prioridade": "Score de Criticidade (ICP)",
                    },
                    hover_data=["percentual_registros", "negativos", "taxa_atrito_pct", "score_prioridade"],
                    text_auto=True,
                    color_discrete_sequence=["#DC2626"],
                )
                fig_dif.update_layout(height=420)
                st.plotly_chart(fig_dif, use_container_width=True)
            else:
                st.info("Não foram identificadas dores específicas no recorte selecionado.")

        st.divider()
        st.subheader("2. Funcionalidades e Módulos Mais Demandados / a Implementar")
        df_func = explodir_campo_multivalorado(df, "funcionalidades")
        if not df_func.empty:
            col_f1, col_f2 = st.columns([3, 2])
            with col_f1:
                df_func_plot = df_func.sort_values("mencoes", ascending=True)
                fig_func = px.bar(
                    df_func_plot,
                    x="mencoes",
                    y="item",
                    orientation="h",
                    title="Ranking de Funcionalidades e Módulos de ERP Mais Discutidos",
                    labels={
                        "mencoes": "Total de Menções",
                        "item": "Módulo / Funcionalidade",
                        "score_prioridade": "Score ICP",
                    },
                    hover_data=["percentual_registros", "positivos", "negativos", "taxa_atrito_pct", "score_prioridade"],
                    text_auto=True,
                    color_discrete_sequence=["#0284C7"],
                )
                fig_func.update_layout(height=440)
                st.plotly_chart(fig_func, use_container_width=True)

            with col_f2:
                st.markdown("##### Detalhamento de Demanda e Score ICP por Módulo")
                st.dataframe(
                    df_func.rename(
                        columns={
                            "item": "Funcionalidade / Módulo",
                            "mencoes": "Menções",
                            "percentual_registros": "% Base",
                            "positivos": "Pos",
                            "negativos": "Neg",
                            "neutros": "Neu",
                            "taxa_atrito_pct": "% Atrito",
                            "score_prioridade": "Score ICP",
                        }
                    ),
                    use_container_width=True,
                    height=400,
                    hide_index=True,
                )

        st.divider()
        st.subheader("3. Matriz Causa-Efeito: Dores do Mercado × Funcionalidades de ERP Demandadas")
        st.caption(
            "Cruza as dores operacionais relatadas com os módulos de software mencionados no mesmo contexto, "
            "revelando quais funcionalidades resolvem diretamente cada gargalo do mercado."
        )
        df_matriz = gerar_matriz_dor_vs_funcionalidade(df)
        if not df_matriz.empty:
            pivot_matriz = df_matriz.pivot(
                index="dor", columns="funcionalidade", values="ocorrencias"
            ).fillna(0).astype(int)
            fig_heat = px.imshow(
                pivot_matriz,
                text_auto=True,
                aspect="auto",
                color_continuous_scale="Blues",
                labels={
                    "x": "Funcionalidade / Módulo de ERP Demandado",
                    "y": "Dor / Gargalo Operacional Relatado",
                    "color": "Coocorrências",
                },
                title="Mapa de Calor: Coocorrência entre Dores Operacionais e Módulos de ERP",
            )
            fig_heat.update_layout(height=460)
            st.plotly_chart(fig_heat, use_container_width=True)

        st.divider()
        st.subheader("4. Recomendações Estratégicas e Roadmap para a Integra Engenharia de Sistemas")
        st.caption(
            "Matriz priorizada pelo volume de demanda e pelo Índice de Criticidade e Prioridade (ICP = Menções + 1,5 × Relatos Críticos)."
        )
        df_recomendacoes = gerar_plano_recomendacoes(df)
        if not df_recomendacoes.empty:
            st.dataframe(
                df_recomendacoes,
                use_container_width=True,
                hide_index=True,
            )

        st.divider()
        st.subheader("5. Comparativo entre Plataformas e Evolução Temporal")
        col_m3, col_m4 = st.columns(2)

        with col_m3:
            df_assunto_plat = (
                df.groupby(["assunto", "plataforma"], as_index=False)
                .size()
                .rename(columns={"size": "quantidade"})
            )
            fig_ap = px.bar(
                df_assunto_plat,
                x="assunto",
                y="quantidade",
                color="plataforma",
                barmode="group",
                title="Distribuição de Assuntos por Plataforma",
                labels={
                    "assunto": "Assunto",
                    "quantidade": "Quantidade de Registros",
                    "plataforma": "Plataforma",
                },
                color_discrete_map=CORES_PLATAFORMA,
                text_auto=True,
            )
            fig_ap.update_layout(height=400)
            st.plotly_chart(fig_ap, use_container_width=True)

        with col_m4:
            df_temp = df.copy()
            df_temp["data_mes"] = (
                pd.to_datetime(df_temp["data_publicacao"], utc=True, errors="coerce")
                .dt.strftime("%Y-%m")
            )
            df_temp_valid = df_temp.dropna(subset=["data_mes"])
            if not df_temp_valid.empty:
                df_serie = (
                    df_temp_valid.groupby(["data_mes", "plataforma"], as_index=False)
                    .size()
                    .rename(columns={"size": "quantidade"})
                    .sort_values("data_mes")
                )
                fig_temp = px.line(
                    df_serie,
                    x="data_mes",
                    y="quantidade",
                    color="plataforma",
                    markers=True,
                    title="Evolução Temporal dos Registros por Plataforma (Mês/Ano)",
                    labels={
                        "data_mes": "Período (Ano-Mês)",
                        "quantidade": "Volume de Registros",
                        "plataforma": "Plataforma",
                    },
                    color_discrete_map=CORES_PLATAFORMA,
                )
                fig_temp.update_layout(height=400)
                st.plotly_chart(fig_temp, use_container_width=True)
            else:
                st.info("Os registros filtrados não possuem datas de publicação válidas para série temporal.")

        st.subheader("📊 Métricas de Engajamento por Plataforma (Sem Comparação Direta Entre Redes)")
        st.caption(
            "Nota técnica (Seção 4.2): Curtidas no YouTube/Instagram, votos positivos (upvotes) no Reddit e "
            "visualizações possuem semânticas distintas e são apresentados separadamente por plataforma."
        )
        cols_eng = st.columns(4)
        for idx, plat_nome in enumerate(["YouTube", "Instagram", "Reddit", "LinkedIn"]):
            df_p = df[df["plataforma"] == plat_nome]
            with cols_eng[idx]:
                st.markdown(f"#### {plat_nome}")
                if df_p.empty:
                    st.caption(f"Sem registros de {plat_nome} para os filtros atuais.")
                else:
                    if plat_nome == "Reddit":
                        label_like = "Upvotes (Votos)"
                    elif plat_nome == "LinkedIn":
                        label_like = "Reações B2B (Likes)"
                    else:
                        label_like = "Curtidas (Likes)"
                    soma_likes = df_p["curtidas"].dropna().sum()
                    soma_coms = df_p["comentarios"].dropna().sum()
                    soma_shares = df_p["compartilhamentos"].dropna().sum()
                    soma_views = df_p["visualizacoes"].dropna().sum()
                    st.write(f"- **Total de registros:** {len(df_p):,}".replace(",", "."))
                    st.write(f"- **{label_like}:** {int(soma_likes):,}".replace(",", "."))
                    st.write(f"- **Comentários reportados:** {int(soma_coms):,}".replace(",", "."))
                    if not df_p["compartilhamentos"].dropna().empty:
                        st.write(f"- **Compartilhamentos/Reposts:** {int(soma_shares):,}".replace(",", "."))
                    if not df_p["visualizacoes"].dropna().empty:
                        st.write(f"- **Visualizações:** {int(soma_views):,}".replace(",", "."))
                    else:
                        st.write("- **Visualizações:** *Não aplicável / Não disponível*")

    # =========================================================================
    # ABA 3 — DETALHAMENTO E CONSULTAS HIVEQL
    # =========================================================================
    with aba3:
        st.subheader("Registros Individuais Normalizados, Classificados e Enriquecidos")
        colunas_exibicao = [
            "plataforma",
            "tipo_registro",
            "data_publicacao",
            "palavra_chave",
            "assunto",
            "temas_adicionais",
            "funcionalidades",
            "dores_relatadas",
            "sentimento",
            "texto",
            "curtidas",
            "comentarios",
            "visualizacoes",
            "origem_dado",
            "url_publicacao",
        ]
        colunas_presentes = [c for c in colunas_exibicao if c in df.columns]
        st.dataframe(
            df[colunas_presentes],
            use_container_width=True,
            height=460,
            hide_index=True,
        )

        csv_bytes = df[colunas_presentes].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="⬇️ Baixar Recorte Filtrado (CSV UTF-8-SIG)",
            data=csv_bytes,
            file_name="recorte_inteligencia_mercado_integra.csv",
            mime="text/csv",
        )

        st.divider()
        st.subheader("🐝 Resultados Executados das Consultas Analíticas HiveQL (`Apache Hive`)")
        arquivos_hive = sorted(HIVE_RESULTS_DIR.glob("consulta_*.csv")) if HIVE_RESULTS_DIR.exists() else []
        if arquivos_hive:
            opcoes_hive = {arq.stem: arq for arq in arquivos_hive}
            consulta_escolhida = st.selectbox(
                "Selecione a Consulta HiveQL para visualizar o resultado:",
                options=list(opcoes_hive.keys()),
            )
            if consulta_escolhida:
                df_hive_res = pd.read_csv(opcoes_hive[consulta_escolhida], encoding="utf-8-sig")
                st.dataframe(df_hive_res, use_container_width=True, hide_index=True)
        else:
            st.info(
                "Execute `python main.py --hive` ou clique em 'Atualizar Tratamento, HDFS e Hive' "
                "na barra lateral para gerar as tabelas de resultado do HiveQL."
            )

        with st.expander("🔍 Inspecionar Código-Fonte HiveQL (`hive/consultas.hql`)"):
            caminho_hql = HIVE_DIR / "consultas.hql"
            if caminho_hql.exists():
                st.code(caminho_hql.read_text(encoding="utf-8"), language="sql")


if __name__ == "__main__":
    renderizar_dashboard()
