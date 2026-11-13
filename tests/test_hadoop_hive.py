"""
Testes unitários das FASES 4 e 5 — Hadoop/HDFS e Apache Hive (Sem Docker).
Valida a criação de diretórios e armazenamento no HDFS, os scripts DDL/DQL em HiveQL
e a execução real das 10 consultas analíticas de `hive/consultas.hql`.
"""

from pathlib import Path
import tempfile

from config.settings import HIVE_DIR
from hadoop.scripts.enviar_hdfs import (
    HDFS_DIRECTORIES,
    criar_diretorios_hdfs,
    enviar_arquivo_para_hdfs,
    listar_arquivos_hdfs,
    verificar_arquivo_hdfs,
)
from hive.executar_hive import executar_fluxo_hive, extrair_consultas_hql
from processamento.normalizar_dados import normalizar_registros


def test_hdfs_directory_structure_matches_spec():
    """Verifica se os diretórios configurados seguem a estrutura da Seção 6."""
    assert "/projeto_integrador/dados_brutos/youtube" in HDFS_DIRECTORIES
    assert "/projeto_integrador/dados_brutos/instagram" in HDFS_DIRECTORIES
    assert "/projeto_integrador/dados_brutos/reddit" in HDFS_DIRECTORIES
    assert "/projeto_integrador/dados_tratados/multiplataforma" in HDFS_DIRECTORIES


def test_hdfs_operations_without_docker():
    """Testa criação de diretórios, envio, verificação e listagem no HDFS sem Docker."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hdfs_root = Path(tmpdir) / "hdfs_storage"
        criados = criar_diretorios_hdfs(root_dir=hdfs_root)
        assert len(criados) == 4

        sample_file = Path(tmpdir) / "dados_multiplataforma.csv"
        sample_file.write_text("plataforma,id_registro\nYouTube,yt1\n", encoding="utf-8")

        destino = "/projeto_integrador/dados_tratados/multiplataforma/dados_multiplataforma.csv"
        enviar_arquivo_para_hdfs(sample_file, destino, root_dir=hdfs_root)

        assert verificar_arquivo_hdfs(destino, root_dir=hdfs_root) is True
        listagem = listar_arquivos_hdfs("/projeto_integrador", root_dir=hdfs_root)
        assert any("dados_multiplataforma.csv" in linha for linha in listagem)


def test_hive_ddl_script_exists_and_creates_external_table():
    """Verifica se hive/criar_tabela.hql define a tabela externa sobre o diretório HDFS."""
    ddl_path = HIVE_DIR / "criar_tabela.hql"
    assert ddl_path.exists()
    ddl = ddl_path.read_text(encoding="utf-8")
    assert "CREATE EXTERNAL TABLE" in ddl.upper()
    assert "/projeto_integrador/dados_tratados/multiplataforma" in ddl
    assert "plataforma" in ddl
    assert "sentimento" in ddl
    assert "assunto" in ddl


def test_hive_consultas_execution_all_10_queries():
    """Verifica se todas as 12 consultas SELECT de hive/consultas.hql executam com sucesso."""
    statements = extrair_consultas_hql(HIVE_DIR / "consultas.hql")
    select_queries = [s for s in statements if s.upper().startswith("SELECT")]
    assert len(select_queries) == 12

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        df_teste = normalizar_registros(
            registros_youtube=[
                {
                    "id": "yt1",
                    "title": "Implantação de ERP rápida e eficiente com emissão de nota fiscal",
                    "likeCount": 50,
                    "viewCount": 500,
                    "uploadDate": "2026-05-01T10:00:00Z",
                    "_coleta_meta": {"palavra_chave": "Implantação de ERP"},
                }
            ],
            registros_reddit=[
                {
                    "id": "rd1",
                    "title": "Suporte com erro e lentidão no sistema financeiro",
                    "upVotes": 20,
                    "createdAt": "2026-05-02T12:00:00Z",
                    "_coleta_meta": {"palavra_chave": "Suporte técnico de sistemas"},
                }
            ],
        )
        csv_temp = tmp_path / "dados_multiplataforma.csv"
        df_teste.to_csv(csv_temp, index=False, encoding="utf-8-sig")

        out_hive = tmp_path / "hive_resultados"
        res = executar_fluxo_hive(caminho_csv_override=csv_temp, output_dir=out_hive)
        assert res["success"] is True
        assert res["queries_executed"] == 12
        assert (out_hive / "resumo_consultas_hive.json").exists()
        assert (out_hive / "consulta_01_distribuicao_plataforma.csv").exists()
        assert (out_hive / "consulta_11_funcionalidades_demandadas.csv").exists()
        assert (out_hive / "consulta_12_dores_operacionais_mercado.csv").exists()
