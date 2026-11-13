"""
Executor unificado de todos os testes unitários do Projeto Integrador V – B.
Compatível tanto com `pytest` quanto com execução direta (`python tests/run_all_tests.py`).
"""

import inspect
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests import (
    test_coleta,
    test_config,
    test_dashboard,
    test_hadoop_hive,
    test_processamento,
)


def main() -> int:
    modulos = [
        test_config,
        test_coleta,
        test_processamento,
        test_hadoop_hive,
        test_dashboard,
    ]
    total = 0
    falhas = 0

    print("=" * 72)
    print("EXECUTANDO SUITE DE TESTES — PROJETO INTEGRADOR V-B (INTEGRA ENGENHARIA)")
    print("=" * 72)

    for mod in modulos:
        nome_mod = mod.__name__
        funcoes = [
            (nome, fn)
            for nome, fn in inspect.getmembers(mod, inspect.isfunction)
            if nome.startswith("test_")
        ]
        for nome_fn, fn in funcoes:
            total += 1
            try:
                fn()
                print(f"[PASSOU] {nome_mod}.{nome_fn}")
            except Exception as exc:
                falhas += 1
                print(f"[FALHOU] {nome_mod}.{nome_fn}: {exc}")

    print("-" * 72)
    print(f"Total de testes executados: {total} | Sucessos: {total - falhas} | Falhas: {falhas}")
    print("=" * 72)
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
