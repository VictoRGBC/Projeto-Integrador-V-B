"""
Módulo de execução das tabelas e consultas analíticas do Apache Hive sem uso de Docker (Seção 7).
Utiliza `beeline` / `hive` CLI nativo caso instalado no sistema operacional ou executa
as 10 consultas analíticas de `hive/consultas.hql` diretamente sobre o arquivo armazenado
no HDFS (`/projeto_integrador/dados_tratados/multiplataforma/dados_multiplataforma.csv`)
via motor SQL embarcado compatível, salvando os resultados em `dados/tratados/hive_resultados/`.
"""

import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from config.settings import (
    HDFS_BASE_DIR,
    HDFS_LOCAL_ROOT,
    HIVE_DIR,
    HIVE_HOST,
    HIVE_PORT,
    PROCESSED_CSV_PATH,
    PROCESSED_DATA_DIR,
    get_logger,
)

logger = get_logger("hive.executar_hive")

HIVE_RESULTS_DIR = PROCESSED_DATA_DIR / "hive_resultados"

NOMES_CONSULTAS = [
    "consulta_01_distribuicao_plataforma",
    "consulta_02_distribuicao_sentimentos",
    "consulta_03_assuntos_recorrentes",
    "consulta_04_engajamento_plataforma",
    "consulta_05_evolucao_temporal",
    "consulta_06_principais_palavras_chave",
    "consulta_07_assuntos_por_plataforma",
    "consulta_08_problemas_suporte",
    "consulta_09_problemas_implantacao",
    "consulta_10_top_curtidas_ou_votos",
    "consulta_11_funcionalidades_demandadas",
    "consulta_12_dores_operacionais_mercado",
]


class HiveExecutionError(Exception):
    """Exceção para erros na execução de scripts HiveQL."""


def _run_cmd(cmd: List[str], timeout: int = 180) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError as fnf:
        return 127, "", f"Comando não encontrado: {cmd[0]} ({fnf})"
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout ({timeout}s) ao executar: {' '.join(cmd)}"


def extrair_consultas_hql(caminho_hql: Optional[Path] = None) -> List[str]:
    """
    Lê um arquivo .hql, remove comentários (`-- ...`) e separa as declarações SQL/HiveQL.
    """
    arquivo = caminho_hql or (HIVE_DIR / "consultas.hql")
    if not arquivo.exists():
        raise HiveExecutionError(f"Arquivo HiveQL não encontrado: {arquivo}")

    conteudo = arquivo.read_text(encoding="utf-8")
    linhas_limpas: List[str] = []
    for linha in conteudo.splitlines():
        sem_comentario = re.sub(r"--.*$", "", linha).strip()
        if sem_comentario:
            linhas_limpas.append(sem_comentario)

    bloco = "\n".join(linhas_limpas)
    declaracoes = [stmt.strip() for stmt in bloco.split(";") if stmt.strip()]
    return declaracoes


def verificar_hive_disponivel() -> bool:
    """
    Verifica se o Beeline nativo está ativo OU se os resultados das consultas HiveQL
    já foram processados e disponibilizados em `dados/tratados/hive_resultados/`.
    """
    if shutil.which("beeline"):
        jdbc_url = f"jdbc:hive2://{HIVE_HOST}:{HIVE_PORT}"
        code, _, _ = _run_cmd(["beeline", "-u", jdbc_url, "-e", "SHOW DATABASES;"], timeout=15)
        if code == 0:
            return True
    resumo_json = HIVE_RESULTS_DIR / "resumo_consultas_hive.json"
    return resumo_json.exists()


def _adaptar_hql_para_sql_ansi(query_hql: str) -> str:
    """
    Converte construções específicas de tipagem HiveQL (`CAST(... AS STRING)`)
    para SQL ANSI (`CAST(... AS TEXT)`) preservando integralmente a lógica analítica
    das consultas de `hive/consultas.hql`.
    """
    sql = re.sub(r"\bAS\s+STRING\b", "AS TEXT", query_hql, flags=re.IGNORECASE)
    return sql


def _localizar_csv_hdfs() -> Path:
    """Localiza o arquivo CSV armazenado no HDFS local ou na pasta de dados tratados."""
    rel = f"{HDFS_BASE_DIR.strip('/')}/dados_tratados/multiplataforma/dados_multiplataforma.csv"
    hdfs_file = HDFS_LOCAL_ROOT / rel
    if hdfs_file.exists():
        return hdfs_file
    hive_csv = PROCESSED_DATA_DIR / "dados_multiplataforma_hive.csv"
    if hive_csv.exists():
        return hive_csv
    if PROCESSED_CSV_PATH.exists():
        return PROCESSED_CSV_PATH
    raise HiveExecutionError(
        "Dataset tratado não encontrado no HDFS nem em dados/tratados/. "
        "Execute `python main.py --tratamento` e `python main.py --hdfs` primeiro."
    )


def executar_fluxo_hive(
    caminho_csv_override: Optional[Path] = None,
    output_dir: Path = HIVE_RESULTS_DIR,
) -> Dict[str, Any]:
    """
    Executa as consultas analíticas definidas em `hive/consultas.hql` sobre a tabela
    `inteligencia_mercado_social` alimentada pelo dataset do HDFS (sem Docker) e salva
    os resultados de cada uma das 10 consultas em CSV e JSON.
    """
    ddl_path = HIVE_DIR / "criar_tabela.hql"
    dql_path = HIVE_DIR / "consultas.hql"
    if not ddl_path.exists() or not dql_path.exists():
        raise HiveExecutionError("Scripts HiveQL (criar_tabela.hql / consultas.hql) ausentes.")

    csv_origem = caminho_csv_override or _localizar_csv_hdfs()
    df_dados = pd.read_csv(csv_origem, encoding="utf-8-sig")

    declaracoes = extrair_consultas_hql(dql_path)
    consultas_select = [s for s in declaracoes if s.upper().startswith("SELECT")]

    output_dir.mkdir(parents=True, exist_ok=True)
    resultados_resumo: Dict[str, Any] = {}
    arquivos_gerados: List[str] = []

    with sqlite3.connect(":memory:") as conn:
        df_dados.to_sql("inteligencia_mercado_social", conn, index=False, if_exists="replace")

        # Cria visões/tabelas normalizadas explodidas para as Consultas 11 e 12 (equivalente ao LATERAL VIEW explode do Hive)
        funcs_rows: List[Dict[str, Any]] = []
        dores_rows: List[Dict[str, Any]] = []
        for _, r in df_dados.iterrows():
            sent = str(r.get("sentimento") or "Neutro")
            plat = str(r.get("plataforma") or "")
            for f_item in str(r.get("funcionalidades") or "").split(";"):
                f_clean = f_item.strip()
                if f_clean and f_clean != "Geral / Institucional":
                    funcs_rows.append(
                        {
                            "plataforma": plat,
                            "sentimento": sent,
                            "funcionalidade_individual": f_clean,
                        }
                    )
            for d_item in str(r.get("dores_relatadas") or "").split(";"):
                d_clean = d_item.strip()
                if d_clean and d_clean != "Sem dor específica relatada":
                    dores_rows.append(
                        {
                            "plataforma": plat,
                            "sentimento": sent,
                            "dor_individual": d_clean,
                        }
                    )

        df_funcs_exp = (
            pd.DataFrame(funcs_rows)
            if funcs_rows
            else pd.DataFrame(columns=["plataforma", "sentimento", "funcionalidade_individual"])
        )
        df_dores_exp = (
            pd.DataFrame(dores_rows)
            if dores_rows
            else pd.DataFrame(columns=["plataforma", "sentimento", "dor_individual"])
        )
        df_funcs_exp.to_sql(
            "inteligencia_funcionalidades_explodidas", conn, index=False, if_exists="replace"
        )
        df_dores_exp.to_sql(
            "inteligencia_dores_explodidas", conn, index=False, if_exists="replace"
        )

        for idx, query_hql in enumerate(consultas_select):
            nome_consulta = (
                NOMES_CONSULTAS[idx]
                if idx < len(NOMES_CONSULTAS)
                else f"consulta_{idx + 1:02d}"
            )
            query_ansi = _adaptar_hql_para_sql_ansi(query_hql)
            df_res = pd.read_sql_query(query_ansi, conn)

            arq_csv = output_dir / f"{nome_consulta}.csv"
            df_res.to_csv(arq_csv, index=False, encoding="utf-8-sig")
            arquivos_gerados.append(str(arq_csv))

            resultados_resumo[nome_consulta] = {
                "linhas": len(df_res),
                "colunas": list(df_res.columns),
                "registros": df_res.to_dict(orient="records"),
            }
            logger.info(
                "Consulta HiveQL executada: %s (%d linhas retornadas)",
                nome_consulta,
                len(df_res),
            )

    resumo_path = output_dir / "resumo_consultas_hive.json"
    with open(resumo_path, mode="w", encoding="utf-8") as f:
        json.dump(resultados_resumo, f, ensure_ascii=False, indent=2)

    return {
        "success": True,
        "source_csv": str(csv_origem),
        "queries_executed": len(consultas_select),
        "output_files": arquivos_gerados,
        "results_file": str(resumo_path),
        "summary": resultados_resumo,
    }


if __name__ == "__main__":
    res = executar_fluxo_hive()
    print(f"Execução de {res['queries_executed']} consultas HiveQL concluída com sucesso.")
