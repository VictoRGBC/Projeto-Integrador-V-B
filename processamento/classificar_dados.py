"""
Módulo de classificação heurística exploratória de sentimentos, assuntos,
funcionalidades demandadas e dores/dificuldades do mercado de sistemas ERP (Seção 5).

Metodologia: Classificação heurística exploratória baseada em léxico de palavras-chave
e expressões contextuais do domínio de softwares de gestão empresarial (ERP),
suporte técnico, implantação e automação (com suporte multilíngue PT/ES/EN).
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


# Expressões compostas positivas que contêm palavras como 'erro' ou 'falha',
# mas cujo sentido real é POSITIVO (ex: "redução de erros", "evitar falhas").
EXPRESSOES_CONTEXTO_POSITIVO: List[str] = [
    "reducao de erros",
    "reduzindo erros",
    "reduzir erros",
    "evitar falhas",
    "evita falhas",
    "evitando falhas",
    "evitar erros",
    "eliminar erros",
    "elimina erros",
    "eliminar falhas",
    "eliminar retrabalho",
    "sem erros",
    "sem falhas",
    "sem complicacao",
    "sem dor de cabeca",
    "sem perdas",
    "resolver problemas",
    "resolveu o problema",
    "solucionar problemas",
    "ganho de tempo",
    "aumento de produtividade",
    "maior eficiencia",
    "facil de usar",
    "simples de usar",
    "melhor sistema",
    "otimo suporte",
    "excelente suporte",
]

EXPRESSOES_CONTEXTO_NEGATIVO: List[str] = [
    "nao funciona",
    "suporte ruim",
    "suporte lento",
    "suporte demora",
    "sistema lento",
    "sistema travando",
    "muito caro",
    "dificil de usar",
    "cheio de bugs",
    "cheio de erros",
    "muitos erros",
    "falha no sistema",
    "erro no sistema",
    "péssimo atendimento",
    "pessimo atendimento",
    "implantacao falhou",
    "implantacao demorada",
    "perda de dados",
    "perda de dinheiro",
    "nao recomendo",
]

# Léxico heurístico exploratório de sentimentos (Seção 5.1)
TERMOS_POSITIVOS: List[str] = [
    "bom",
    "boa",
    "otimo",
    "otima",
    "excelente",
    "recomendo",
    "recomendavel",
    "eficiente",
    "eficiencia",
    "rapido",
    "rapida",
    "facil",
    "facilitar",
    "gostei",
    "satisfeito",
    "satisfeita",
    "pratico",
    "intuitivo",
    "estavel",
    "agil",
    "agilidade",
    "resolveu",
    "melhorou",
    "melhorar",
    "organizado",
    "confiavel",
    "sucesso",
    "produtivo",
    "produtividade",
    "atendeu",
    "beneficios",
    "vantagens",
    "otimizar",
    "assertividade",
]

TERMOS_NEGATIVOS: List[str] = [
    "ruim",
    "pessimo",
    "pessima",
    "dificil",
    "dificuldade",
    "dificuldades",
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
    "frustracao",
    "atraso",
    "quebra",
    "descaso",
    "precario",
    "caos",
    "prejuizo",
]

# Léxico heurístico de categorias temáticas do mercado de ERP (Seção 5.2 - PT/ES/EN)
MAPA_TEMAS: Dict[str, List[str]] = {
    "Atendimento e suporte": [
        "suporte",
        "soporte",
        "support",
        "atendimento",
        "chamado",
        "chamados",
        "helpdesk",
        "help desk",
        "service desk",
        "sla",
        "ticket",
        "tickets",
        "tecnico",
        "retorno",
        "assistencia",
        "consultor",
        "consultoria",
        "pos-venda",
    ],
    "Implantação": [
        "implantacao",
        "implantacaoerp",
        "consultoraerp",
        "implementacao",
        "implementacion",
        "implementation",
        "implementations",
        "implementaste",
        "implementando",
        "migracao",
        "migration",
        "treinamento",
        "capacitacao",
        "onboarding",
        "parametrizacao",
        "virada",
        "go-live",
        "golive",
        "adocao",
        "setup",
        "configuracao inicial",
        "implantar",
        "estabilizacion",
        "projects fail",
    ],
    "Preço e custo": [
        "preco",
        "precos",
        "custo",
        "custos",
        "coste",
        "costes",
        "pricing",
        "mensalidade",
        "licenca",
        "caro",
        "barato",
        "orcamento",
        "investimento",
        "valor",
        "cobranca",
        "cobrancas",
        "contrato",
        "roi",
        "gratuito",
        "gratis",
        "planos",
        "cotice",
        "usd",
    ],
    "Desempenho e lentidão": [
        "desempenho",
        "lentidao",
        "lento",
        "lenta",
        "travando",
        "trava",
        "travou",
        "performance",
        "queda",
        "fora do ar",
        "indisponivel",
        "pesado",
        "instabilidade",
        "instavel",
        "timeout",
        "velocidade",
        "escalabilidade",
        "estabilidade",
    ],
    "Integração e automação": [
        "integracao",
        "integracoes",
        "integracion",
        "integration",
        "integra",
        "integrar",
        "automacao",
        "automatizacion",
        "automatizar",
        "automation",
        "automations",
        "automatica",
        "automatico",
        "api",
        "apis",
        "webhook",
        "sincronizacao",
        "conector",
        "rpa",
        "workflow",
        "importacao",
        "exportacao",
        "inteligencia artificial",
        "ai agents",
        "chatgpt",
        "claude",
    ],
    "Funcionalidades": [
        "funcionalidade",
        "funcionalidades",
        "features",
        "modulo",
        "modulos",
        "relatorio",
        "relatorios",
        "estoque",
        "inventario",
        "inventory",
        "financeiro",
        "finanzas",
        "financials",
        "nota fiscal",
        "nfe",
        "faturamento",
        "contabilidade",
        "contabil",
        "accounting",
        "compras",
        "vendas",
        "logistica",
        "supply chain",
        "dashboard",
        "indicadores",
        "crm",
        "recursos humanos",
        "producao",
    ],
}

# Mapeamento de Funcionalidades e Módulos Demandados (para orientar evolução de produto na Integra)
MAPA_FUNCIONALIDADES: Dict[str, List[str]] = {
    "Emissão Fiscal e Tributária (NF-e / CT-e / SPED)": [
        "nota fiscal",
        "nfe",
        "nf-e",
        "nfce",
        "cte",
        "ct-e",
        "fiscal",
        "tributario",
        "sped",
        "sefaz",
        "imposto",
        "impostos",
        "faturamento",
        "invoice",
    ],
    "Gestão Financeira, Contábil e Fluxo de Caixa": [
        "financeiro",
        "fluxo de caixa",
        "contas a pagar",
        "contas a receber",
        "conciliacao",
        "boleto",
        "pix",
        "orcamentario",
        "contabil",
        "contabilidade",
        "finanzas",
        "financials",
        "accounting",
    ],
    "Controle de Estoque, Compras e Logística": [
        "estoque",
        "inventario",
        "inventory",
        "compras",
        "fornecedores",
        "logistica",
        "supply chain",
        "mercadorias",
        "armazem",
        "wms",
        "rotas",
        "transportadora",
    ],
    "Integração via API, Webhooks e Marketplaces": [
        "api",
        "apis",
        "webhook",
        "integracao",
        "integracoes",
        "marketplace",
        "marketplaces",
        "shopee",
        "mercado livre",
        "e-commerce",
        "ecommerce",
        "conector",
        "pluga",
    ],
    "Dashboards BI, Relatórios e Indicadores (KPIs)": [
        "relatorio",
        "relatorios",
        "dashboard",
        "dashboards",
        "indicadores",
        "kpi",
        "kpis",
        "bi",
        "business intelligence",
        "data driven",
        "analytics",
        "metas",
    ],
    "Automação com IA e Workflows Operacionais": [
        "automacao",
        "automatizar",
        "automatizacion",
        "inteligencia artificial",
        "ia",
        "ai",
        "claude",
        "rpa",
        "workflow",
        "orquestracao",
        "eliminar tarefas manuais",
    ],
    "CRM, Gestão Comercial e Frente de Caixa (PDV)": [
        "crm",
        "vendas",
        "comercial",
        "pre-venda",
        "pos-venda",
        "pdv",
        "frente de caixa",
        "pedido",
        "pedidos",
        "clientes",
        "sales",
    ],
    "Cloud ERP (Nuvem) e Acesso Mobile": [
        "nuvem",
        "cloud",
        "saas",
        "web",
        "mobile",
        "celular",
        "aplicativo",
        "remoto",
        "online",
    ],
    "Portal de Suporte, Helpdesk e Treinamento Guiado": [
        "suporte",
        "helpdesk",
        "chamado",
        "chamados",
        "treinamento",
        "onboarding",
        "curso",
        "tutorial",
        "documentacao",
    ],
}

# Mapeamento de Dores, Gargalos e Problemas Recorrentes Relatados no Mercado
MAPA_DORES_MERCADO: Dict[str, List[str]] = {
    "Retrabalho Manual e Planilhas Descentralizadas": [
        "planilha",
        "excel",
        "caderno",
        "manual",
        "manuais",
        "retrabalho",
        "duplicidade",
        "perda de informacoes",
        "descentralizado",
    ],
    "Complexidade na Implantação e Parametrização": [
        "implantacao",
        "migracao",
        "parametrizacao",
        "virada",
        "go-live",
        "adaptar",
        "complexo",
        "complicado",
        "demorado",
    ],
    "Deficiência em Suporte Técnico e Atendimento": [
        "suporte ruim",
        "suporte lento",
        "demora no suporte",
        "falta de suporte",
        "atendimento",
        "chamado",
        "sla",
        "sem retorno",
        "consultoria",
    ],
    "Falhas de Integração entre Setores e Sistemas": [
        "falta de integracao",
        "nao integra",
        "integrar",
        "silos",
        "falhas humanas",
        "erros de coleta",
        "sincronizacao",
    ],
    "Lentidão, Travamentos e Instabilidade de Sistema": [
        "lento",
        "lentidao",
        "trava",
        "travando",
        "pesado",
        "queda",
        "instavel",
        "indisponivel",
        "bug",
        "bugs",
    ],
    "Preocupação com Custos, Licenças e ROI": [
        "caro",
        "custo",
        "custos",
        "mensalidade",
        "licenca",
        "orcamento",
        "perda de dinheiro",
        "prejuizo",
    ],
    "Dificuldade de Usabilidade e Falta de Treinamento": [
        "dificil",
        "dificuldades",
        "complicado demais",
        "treinamento",
        "capacitacao",
        "aprender",
        "usabilidade",
    ],
}


def classificar_sentimento(texto: str) -> str:
    """
    Classifica o sentimento de um texto de forma heurística exploratória em:
    'Positivo', 'Negativo' ou 'Neutro'.
    Trata expressões contextuais (ex: 'redução de erros', 'evitar falhas') para evitar
    falsos negativos em textos explicativos ou elogiosos.
    """
    texto_norm = _normalizar_para_busca(texto)
    if not texto_norm:
        return "Neutro"

    score_pos = 0
    score_neg = 0

    texto_trabalho = texto_norm
    for expr_pos in EXPRESSOES_CONTEXTO_POSITIVO:
        if expr_pos in texto_trabalho:
            score_pos += 2
            texto_trabalho = texto_trabalho.replace(expr_pos, " ")

    for expr_neg in EXPRESSOES_CONTEXTO_NEGATIVO:
        if expr_neg in texto_trabalho:
            score_neg += 2
            texto_trabalho = texto_trabalho.replace(expr_neg, " ")

    palavras = set(re.findall(r"\b\w+\b", texto_trabalho))

    for termo in TERMOS_POSITIVOS:
        if " " in termo:
            if termo in texto_trabalho:
                score_pos += 1
        elif termo in palavras:
            score_pos += 1

    for termo in TERMOS_NEGATIVOS:
        if " " in termo:
            if termo in texto_trabalho:
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

    contagem_temas.sort(key=lambda item: item[1], reverse=True)
    assunto_principal = contagem_temas[0][0]
    adicionais = [cat for cat, _ in contagem_temas[1:]]
    return assunto_principal, "; ".join(adicionais)


def classificar_assunto(texto: str) -> str:
    """Retorna apenas o assunto principal identificado para o texto."""
    principal, _ = identificar_temas(texto)
    return principal


def identificar_funcionalidades(texto: str) -> str:
    """
    Extrai os módulos e funcionalidades de ERP mencionados ou demandados no registro.
    Retorna string com categorias separadas por '; ' ou 'Geral / Institucional'.
    """
    texto_norm = _normalizar_para_busca(texto)
    if not texto_norm:
        return "Geral / Institucional"

    palavras = set(re.findall(r"\b\w+\b", texto_norm))
    encontradas: List[Tuple[str, int]] = []

    for func_nome, termos in MAPA_FUNCIONALIDADES.items():
        hits = 0
        for termo in termos:
            if " " in termo:
                if termo in texto_norm:
                    hits += 1
            elif termo in palavras:
                hits += 1
        if hits > 0:
            encontradas.append((func_nome, hits))

    if not encontradas:
        return "Geral / Institucional"

    encontradas.sort(key=lambda x: x[1], reverse=True)
    return "; ".join(nome for nome, _ in encontradas)


def identificar_dores_mercado(texto: str) -> str:
    """
    Extrai as principais dificuldades, gargalos operacionais ou dores de mercado
    mencionadas no registro. Retorna string separada por '; ' ou 'Sem dor específica relatada'.
    """
    texto_norm = _normalizar_para_busca(texto)
    if not texto_norm:
        return "Sem dor específica relatada"

    palavras = set(re.findall(r"\b\w+\b", texto_norm))
    encontradas: List[Tuple[str, int]] = []

    for dor_nome, termos in MAPA_DORES_MERCADO.items():
        hits = 0
        for termo in termos:
            if " " in termo:
                if termo in texto_norm:
                    hits += 1
            elif termo in palavras:
                hits += 1
        if hits > 0:
            encontradas.append((dor_nome, hits))

    if not encontradas:
        return "Sem dor específica relatada"

    encontradas.sort(key=lambda x: x[1], reverse=True)
    return "; ".join(nome for nome, _ in encontradas)
