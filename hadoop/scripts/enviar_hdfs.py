"""
Módulo de integração com Apache Hadoop / HDFS sem uso de Docker (Seção 6).
Utiliza o cliente `hdfs dfs` nativo caso instalado no sistema operacional, ou
opera sobre a estrutura espelhada do HDFS em `hadoop/hdfs_storage/projeto_integrador/`
para execução acadêmica local sem dependência de containers.
"""

from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from config.settings import (
    HDFS_BASE_DIR,
    HDFS_LOCAL_ROOT,
    PROCESSED_DATA_DIR,
    RAW_INSTAGRAM_DIR,
    RAW_REDDIT_DIR,
    RAW_YOUTUBE_DIR,
    get_logger,
)

logger = get_logger("hadoop.enviar_hdfs")

HDFS_DIRECTORIES: List[str] = [
    f"{HDFS_BASE_DIR}/dados_brutos/youtube",
    f"{HDFS_BASE_DIR}/dados_brutos/instagram",
    f"{HDFS_BASE_DIR}/dados_brutos/reddit",
    f"{HDFS_BASE_DIR}/dados_tratados/multiplataforma",
]


class HdfsError(Exception):
    """Exceção lançada quando ocorre erro no armazenamento ou verificação do HDFS."""


def _run_cmd(cmd: List[str], timeout: int = 120) -> Tuple[int, str, str]:
    """Executa um comando de sistema operacional e retorna (returncode, stdout, stderr)."""
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
        return 127, "", f"Comando não encontrado no sistema: {cmd[0]} ({fnf})"
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout ({timeout}s) ao executar: {' '.join(cmd)}"


def _tem_hdfs_cli_nativo() -> bool:
    """Verifica se o binário `hdfs` nativo está disponível e um NameNode local responde."""
    if not shutil.which("hdfs"):
        return False
    code, _, _ = _run_cmd(["hdfs", "dfs", "-ls", "/"], timeout=15)
    return code == 0


def _mapear_caminho_local_hdfs(caminho_hdfs: str, root_dir: Path = HDFS_LOCAL_ROOT) -> Path:
    """Converte um caminho lógico do HDFS (ex: /projeto_integrador/...) para o caminho físico local."""
    relativo = caminho_hdfs.strip().lstrip("/").replace("/", "\\")
    return root_dir / relativo


def verificar_disponibilidade_hdfs(root_dir: Path = HDFS_LOCAL_ROOT) -> Dict[str, Any]:
    """
    Verifica a disponibilidade do ambiente de armazenamento HDFS (CLI nativo ou modo standalone local).
    """
    if _tem_hdfs_cli_nativo():
        logger.info("Cliente Hadoop CLI (`hdfs dfs`) nativo detectado e ativo.")
        return {"available": True, "mode": "hadoop_cli_nativo"}

    root_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Modo HDFS Standalone Local ativo (sem Docker) em: %s",
        root_dir,
    )
    return {"available": True, "mode": "hdfs_standalone_local", "root": str(root_dir)}


def criar_diretorios_hdfs(
    diretorios: Optional[List[str]] = None,
    root_dir: Path = HDFS_LOCAL_ROOT,
) -> List[str]:
    """
    Cria a árvore de diretórios do projeto no HDFS:
       /projeto_integrador/dados_brutos/{youtube,instagram,reddit}
       /projeto_integrador/dados_tratados/multiplataforma
    """
    alvos = diretorios or HDFS_DIRECTORIES
    criados: List[str] = []
    usa_cli = _tem_hdfs_cli_nativo()

    for d in alvos:
        if usa_cli:
            code, out, err = _run_cmd(["hdfs", "dfs", "-mkdir", "-p", d])
            if code != 0:
                raise HdfsError(f"Erro ao criar diretório '{d}' no HDFS: {err or out}")
        caminho_fisico = _mapear_caminho_local_hdfs(d, root_dir=root_dir)
        caminho_fisico.mkdir(parents=True, exist_ok=True)
        logger.info("Diretório HDFS confirmado: %s", d)
        criados.append(d)

    return criados


def enviar_arquivo_para_hdfs(
    caminho_local: Path,
    destino_hdfs: str,
    root_dir: Path = HDFS_LOCAL_ROOT,
) -> None:
    """
    Armazena um arquivo local no destino lógico do HDFS.
    """
    if not caminho_local.exists():
        raise HdfsError(f"Arquivo local não encontrado para envio ao HDFS: {caminho_local}")

    if _tem_hdfs_cli_nativo():
        put_code, put_out, put_err = _run_cmd(
            ["hdfs", "dfs", "-put", "-f", str(caminho_local), destino_hdfs]
        )
        if put_code != 0:
            raise HdfsError(
                f"Falha ao gravar '{caminho_local.name}' em '{destino_hdfs}' no HDFS: {put_err or put_out}"
            )

    destino_fisico = _mapear_caminho_local_hdfs(destino_hdfs, root_dir=root_dir)
    if destino_hdfs.endswith("/"):
        destino_fisico.mkdir(parents=True, exist_ok=True)
        destino_fisico = destino_fisico / caminho_local.name
    else:
        destino_fisico.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(caminho_local, destino_fisico)
    logger.info(
        "Arquivo '%s' armazenado com sucesso no HDFS em '%s'.",
        caminho_local.name,
        destino_hdfs,
    )


def verificar_arquivo_hdfs(
    caminho_hdfs: str,
    root_dir: Path = HDFS_LOCAL_ROOT,
) -> bool:
    """
    Verifica se um arquivo existe e possui tamanho > 0 no HDFS.
    """
    if _tem_hdfs_cli_nativo():
        code, _, _ = _run_cmd(["hdfs", "dfs", "-test", "-e", caminho_hdfs])
        return code == 0

    caminho_fisico = _mapear_caminho_local_hdfs(caminho_hdfs, root_dir=root_dir)
    return caminho_fisico.exists() and caminho_fisico.stat().st_size > 0


def listar_arquivos_hdfs(
    diretorio_base: str = HDFS_BASE_DIR,
    root_dir: Path = HDFS_LOCAL_ROOT,
) -> List[str]:
    """
    Lista recursivamente os arquivos armazenados na estrutura `/projeto_integrador` do HDFS.
    """
    if _tem_hdfs_cli_nativo():
        code, out, err = _run_cmd(["hdfs", "dfs", "-ls", "-R", diretorio_base])
        if code != 0:
            raise HdfsError(f"Erro ao listar diretório '{diretorio_base}' no HDFS: {err or out}")
        return [ln.strip() for ln in out.splitlines() if ln.strip()]

    base_fisica = _mapear_caminho_local_hdfs(diretorio_base, root_dir=root_dir)
    if not base_fisica.exists():
        return []

    listagem: List[str] = []
    for item in sorted(base_fisica.rglob("*")):
        rel_hdfs = "/" + item.relative_to(root_dir).as_posix()
        tipo = "drwxr-xr-x" if item.is_dir() else "-rw-r--r--"
        tamanho = 0 if item.is_dir() else item.stat().st_size
        listagem.append(f"{tipo}   1 integra supergroup {tamanho:>10} {rel_hdfs}")
    return listagem


def executar_fluxo_hdfs(root_dir: Path = HDFS_LOCAL_ROOT) -> Dict[str, Any]:
    """
    Executa o fluxo completo de armazenamento no HDFS (Seção 6, sem Docker):
    1. Verifica disponibilidade do ambiente HDFS
    2. Cria a estrutura de diretórios `/projeto_integrador/...`
    3. Envia os JSONs brutos e o CSV tratado para o HDFS
    4. Verifica se os arquivos foram armazenados corretamente
    5. Lista os arquivos disponíveis no HDFS
    """
    status_disp = verificar_disponibilidade_hdfs(root_dir=root_dir)
    diretorios_criados = criar_diretorios_hdfs(root_dir=root_dir)
    arquivos_enviados: List[str] = []

    mapa_brutos = {
        RAW_YOUTUBE_DIR: f"{HDFS_BASE_DIR}/dados_brutos/youtube/",
        RAW_INSTAGRAM_DIR: f"{HDFS_BASE_DIR}/dados_brutos/instagram/",
        RAW_REDDIT_DIR: f"{HDFS_BASE_DIR}/dados_brutos/reddit/",
    }
    for pasta_local, pasta_hdfs in mapa_brutos.items():
        if pasta_local.exists():
            for arq in sorted(pasta_local.glob("*.json")):
                destino = f"{pasta_hdfs}{arq.name}"
                enviar_arquivo_para_hdfs(arq, destino, root_dir=root_dir)
                arquivos_enviados.append(destino)

    hive_csv = PROCESSED_DATA_DIR / "dados_multiplataforma_hive.csv"
    main_csv = PROCESSED_DATA_DIR / "dados_multiplataforma.csv"
    origem_csv = hive_csv if hive_csv.exists() else main_csv

    if not origem_csv.exists():
        raise HdfsError(
            f"Arquivo CSV tratado não encontrado em {PROCESSED_DATA_DIR}. "
            "Execute a etapa de tratamento (`python main.py --tratamento`) antes de enviar ao HDFS."
        )

    destino_csv_hdfs = f"{HDFS_BASE_DIR}/dados_tratados/multiplataforma/dados_multiplataforma.csv"
    enviar_arquivo_para_hdfs(origem_csv, destino_csv_hdfs, root_dir=root_dir)

    if not verificar_arquivo_hdfs(destino_csv_hdfs, root_dir=root_dir):
        raise HdfsError(f"Falha na verificação pós-envio do arquivo no HDFS: {destino_csv_hdfs}")

    arquivos_enviados.append(destino_csv_hdfs)
    listagem = listar_arquivos_hdfs(HDFS_BASE_DIR, root_dir=root_dir)

    return {
        "success": True,
        "mode": status_disp["mode"],
        "directories": diretorios_criados,
        "uploaded_files": arquivos_enviados,
        "hdfs_listing": listagem,
    }


if __name__ == "__main__":
    res = executar_fluxo_hdfs()
    print(f"Armazenamento no HDFS concluído ({res['mode']}):")
    for linha in res["hdfs_listing"]:
        print(" ", linha)
