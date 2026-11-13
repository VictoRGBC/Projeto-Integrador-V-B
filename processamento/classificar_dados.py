"""
Módulo de classificação heurística exploratória de sentimentos e assuntos (Seção 5).
Metodologia: Classificação heurística exploratória baseada em léxico de palavras-chave
do domínio de softwares de gestão empresarial (ERP), suporte técnico e implantação.
"""

import re
from typing import Dict, List, Tuple
import unicodedata


def _normalizar_para_busca(texto: str) -> str:
    """Converte texto para minúsculas e remove acentos para comparação consistente."""
    if not texto or not isinstance(texto, str):
        return ""
    texto_lower = texto.lower()
    nfkd = unicodedata.normalize("NFKD", texto_lower)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento).strip()


# Léxico heurístico exploratório de sentimentos (Seção 5.1)
TERMOS_POSITIVOS: List[str] = [
    "bom",
    "boa",
    "otimo",
    "otima",
    "excelente",
    "recomendo",
    "eficiente",
    "rapido",
    "rapida",
    "facil",
    "gostei",
    "satisfeito",
    "satisfeita",
    "pratico",
    "intuitivo",
    "estavel",
    "agil",
    "resolveu",
    "melhorou",
    "organizado",
    "confiavel",
    "funciona bem",
    "sucesso",
    "produtivo",
    "atendeu",
]

TERMOS_NEGATIVOS: List[str] = [
    "ruim",
    "pessimo",
    "pessima",
    "dificil",
    "problema",
    "problemas",
    "lento",
    "lenta",
    "lentidao",
    "erro",
    "erros",
    "complicado",
    "complicada",
    "insatisfeito",
    "insatisfeita",
    "falha",
    "falhas",
    "travando",
    "trava",
    "bug",
    "bugs",
    "demora",
    "demorado",
    "instavel",
    "caro",
    "horrivel",
    "frustrante",
    "atraso",
    "nao funciona",
    "quebra",
    "descaso",
    "precario",
]

# Léxico heurístico de categorias temáticas do mercado de ERP (Seção 5.2)
MAPA_TEMAS: Dict[str, List[str]] = {
    "Atendimento e suporte": [
        "suporte",
        "atendimento",
        "chamado",
        "chamados",
        "helpdesk",
        "service desk",
        "sla",
        "ticket",
        "tecnico",
        "retorno",
        "assistencia",
        "consultor",
    ],
    "Implantação": [
        "implantacao",
        "implementacao",
        "migracao",
        "treinamento",
        "onboarding",
        "parametrizacao",
        "virada",
        "go-live",
        "golive",
        "adocao",
        "setup",
        "configuracao inicial",
    ],
    "Preço e custo": [
        "preco",
        "custo",
        "mensalidade",
        "licenca",
        "caro",
        "barato",
        "orcamento",
        "investimento",
        "valor",
        "cobranca",
        "contrato",
        "roi",
    ],
    "Desempenho e lentidão": [
        "desempenho",
        "lentidao",
        "lento",
        "lenta",
        "travando",
        "trava",
        "performance",
        "queda",
        "indisponivel",
        "pesado",
        "instabilidade",
        "instavel",
        "timeout",
        "velocidade",
    ],
    "Integração e automação": [
        "integracao",
        "automacao",
        "api",
        "webhook",
        "sincronizacao",
        "conector",
        "automatizar",
        "rpa",
        "workflow",
        "integrar",
        "importacao",
        "exportacao",
    ],
    "Funcionalidades": [
        "funcionalidade",
        "funcionalidades",
        "modulo",
        "modulos",
        "relatorio",
        "relatorios",
        "estoque",
        "financeiro",
        "nota fiscal",
        "nfe",
        "faturamento",
        "dashboard",
        "cadastro",
        "recurso",
        "interface",
        "usabilidade",
    ],
}


def classificar_sentimento(texto: str) -> str:
    """
    Classifica o sentimento de um texto de forma heurística exploratória em:
    'Positivo', 'Negativo' ou 'Neutro'.
    """
    texto_norm = _normalizar_para_busca(texto)
    if not texto_norm:
        return "Neutro"

    palavras = set(re.findall(r"\b\w+\b", texto_norm))

    score_pos = 0
    score_neg = 0

    for termo in TERMOS_POSITIVOS:
        if " " in termo:
            if termo in texto_norm:
                score_pos += 1
        elif termo in palavras:
            score_pos += 1

    for termo in TERMOS_NEGATIVOS:
        if " " in termo:
            if termo in texto_norm:
                score_neg += 1
        elif termo in palavras:
            score_neg += 1

    if score_pos > score_neg:
        return "Positivo"
    if score_neg > score_pos:
        return "Negativo"
    return "Neutro"


def identificar_temas(texto: str) -> Tuple[str, str]:
    """
    Identifica a categoria temática principal e os temas adicionais presentes no texto.
    Retorna uma tupla: (assunto_principal, temas_adicionais_separados_por_ponto_e_virgula).
    Caso nenhum tema específico seja identificado, retorna ('Outros', '').
    """
    texto_norm = _normalizar_para_busca(texto)
    if not texto_norm:
        return "Outros", ""

    palavras = set(re.findall(r"\b\w+\b", texto_norm))
    contagem_temas: List[Tuple[str, int]] = []

    for categoria, termos in MAPA_TEMAS.items():
        hits = 0
        for termo in termos:
            if " " in termo:
                if termo in texto_norm:
                    hits += 1
            elif termo in palavras:
                hits += 1
        if hits > 0:
            contagem_temas.append((categoria, hits))

    if not contagem_temas:
        return "Outros", ""

    # Ordena pela maior quantidade de termos encontrados, mantendo ordem determinística
    contagem_temas.sort(key=lambda item: item[1], reverse=True)
    assunto_principal = contagem_temas[0][0]
    adicionais = [cat for cat, _ in contagem_temas[1:]]
    return assunto_principal, "; ".join(adicionais)


def classificar_assunto(texto: str) -> str:
    """Retorna apenas o assunto principal identificado para o texto."""
    principal, _ = identificar_temas(texto)
    return principal
