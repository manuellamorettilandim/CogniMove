"""
CogniMove — Fundamentação do Motor de Causa-Raiz (Módulo 2)

Módulo de DADOS: documenta a procedência de cada parâmetro usado por
MotorCausaRaiz (backend/analytics/causa_raiz.py) — quais valores vêm de
literatura técnica (fonte primária/secundária) e quais são estimativas da
equipe sem embasamento quantitativo. Não contém nenhuma lógica de cálculo
de probabilidades; apenas consulta a essa procedência.
"""
from __future__ import annotations

from backend.analytics.causa_raiz import Causa

NIVEL_PRIMARIA = "fonte_primaria"
NIVEL_SECUNDARIA = "fonte_secundaria"
NIVEL_ESTIMATIVA = "estimativa_equipe"

# ── Fontes citadas ──────────────────────────────────────────────────────────

FONTES: dict[str, dict] = {
    "NT195": {
        "titulo": "Influência da chuva na ocorrência dos acidentes de trânsito",
        "orgao": "CET-SP",
        "codigo": "NT 195/96",
        "ano": 1996,
        "url": "https://www.cetsp.com.br/media/20743/nt195.pdf",
        "achado": (
            "Estudo de 24 meses na região da Moóca comparou 938 horas de chuva "
            "com períodos secos pareados: os acidentes praticamente dobraram "
            "(+107,3%). Significativo ao nível de 5%."
        ),
    },
    "NT108": {
        "titulo": "Dimensionamento do Tempo de Amarelo",
        "orgao": "CET-SP",
        "codigo": "NT 108/85",
        "ano": 1985,
        "url": "https://www.cetsp.com.br/media/20515/nt108.pdf",
        "achado": (
            "Amarelo subdimensionado cria a zona de dilema, região em que o "
            "veículo não consegue frear a tempo nem liberar a área de conflito. "
            "No cruzamento Consolação x Caio Prado, o acréscimo de 2 s de "
            "vermelho geral reduziu colisões em 35% e atropelamentos em 60% "
            "em seis meses."
        ),
    },
    "IE2024": {
        "titulo": "A sinalização horizontal na segurança do tráfego",
        "orgao": "Instituto de Engenharia",
        "codigo": None,
        "ano": 2024,
        "url": (
            "https://www.institutodeengenharia.org.br/site/wp-content/uploads/"
            "2024/03/Instituto-de-Engenharia_A-Sin.-Horiz.-na-Seguranca-do-"
            "Transito-06.03.2024.pdf"
        ),
        "achado": (
            "55% dos acidentes fatais ocorrem à noite ou com pouca luz, embora "
            "apenas 25% das viagens sejam noturnas. A chuva eleva a taxa de "
            "acidentes em cerca de 57%; a chuva noturna, em cerca de 80%. "
            "A retrorrefletividade da pintura decai continuamente desde a "
            "aplicação."
        ),
    },
}

# ── Procedência dos modificadores contextuais (chaves de MotorCausaRaiz.MODIFICADORES) ──

FUNDAMENTACAO_MODIFICADORES: dict[str, dict] = {
    "chuva_forte": {
        "nivel": NIVEL_PRIMARIA,
        "fontes": ["NT195"],
        "justificativa": (
            "Estudo da CET-SP mediu aumento de 107,3% nos acidentes sob chuva em "
            "São Paulo. A direção e a importância relativa do fator estão "
            "ancoradas em fonte; a magnitude do incremento é calibração da "
            "equipe."
        ),
    },
    "horario_pico": {
        "nivel": NIVEL_ESTIMATIVA,
        "fontes": [],
        "justificativa": (
            "Direção plausível: maior densidade de veículos eleva a chance de "
            "bloqueio de cruzamento. Sem fonte quantitativa localizada."
        ),
    },
    "obra_viaria": {
        "nivel": NIVEL_ESTIMATIVA,
        "fontes": [],
        "justificativa": (
            "Direção plausível: desvios e sinalização provisória reduzem a "
            "legibilidade da via. Sem fonte quantitativa localizada."
        ),
    },
    "dia_jogo": {
        "nivel": NIVEL_ESTIMATIVA,
        "fontes": [],
        "justificativa": (
            "Direção plausível: evento de grande porte concentra demanda em "
            "janelas curtas. Sem fonte quantitativa localizada."
        ),
    },
    "feriado": {
        "nivel": NIVEL_ESTIMATIVA,
        "fontes": [],
        "justificativa": (
            "Direção plausível: maior proporção de condutores não habituados à "
            "via. Sem fonte quantitativa localizada."
        ),
    },
}

# ── Procedência das causas-raiz (valores do enum Causa em causa_raiz.py) ────

_JUSTIFICATIVA_ESTIMATIVA_CAUSA = (
    "Direção plausível segundo a literatura consultada. Sem fonte quantitativa "
    "localizada; magnitude arbitrada pela equipe."
)

FUNDAMENTACAO_CAUSAS: dict[str, dict] = {
    Causa.TEMPO_SEMAFORICO_INADEQUADO.value: {
        "nivel": NIVEL_PRIMARIA,
        "fontes": ["NT108"],
        "justificativa": (
            "A NT 108/85 descreve a zona de dilema criada por amarelo "
            "subdimensionado: o condutor não consegue frear nem liberar a área "
            "de conflito a tempo. Há caso documentado de redução de colisões "
            "com ajuste do entreverdes."
        ),
    },
    Causa.SINALIZACAO_POUCO_VISIVEL.value: {
        "nivel": NIVEL_SECUNDARIA,
        "fontes": ["IE2024"],
        "justificativa": (
            "Baixa visibilidade concentra acidentes graves: 55% dos fatais "
            "ocorrem à noite, embora só 25% das viagens sejam noturnas."
        ),
    },
    Causa.PINTURA_DESGASTADA_AUSENTE.value: {
        "nivel": NIVEL_SECUNDARIA,
        "fontes": ["IE2024"],
        "justificativa": (
            "A retrorrefletividade da sinalização horizontal decai "
            "continuamente desde a aplicação, sem degradação visualmente óbvia "
            "à luz do dia."
        ),
    },
    Causa.CONGESTIONAMENTO.value: {
        "nivel": NIVEL_ESTIMATIVA,
        "fontes": [],
        "justificativa": _JUSTIFICATIVA_ESTIMATIVA_CAUSA,
    },
    Causa.CONDUTA_DO_CONDUTOR.value: {
        "nivel": NIVEL_ESTIMATIVA,
        "fontes": [],
        "justificativa": _JUSTIFICATIVA_ESTIMATIVA_CAUSA,
    },
    Causa.AUSENCIA_DE_SEGREGADOR_FISICO.value: {
        "nivel": NIVEL_ESTIMATIVA,
        "fontes": [],
        "justificativa": _JUSTIFICATIVA_ESTIMATIVA_CAUSA,
    },
}

_JUSTIFICATIVA_DESCONHECIDA = (
    "Chave não catalogada em fundamentacao.py. Tratada como estimativa da "
    "equipe até que a procedência seja documentada."
)


def _procedencia(tabela: dict[str, dict], chave: str) -> dict:
    """Monta o dict de procedência resolvendo as siglas de FONTES."""
    entrada = tabela.get(chave)
    if entrada is None:
        return {
            "nivel": NIVEL_ESTIMATIVA,
            "fontes": [],
            "justificativa": _JUSTIFICATIVA_DESCONHECIDA,
        }
    return {
        "nivel": entrada["nivel"],
        "fontes": [FONTES[sigla] for sigla in entrada["fontes"]],
        "justificativa": entrada["justificativa"],
    }


def procedencia_causa(nome_causa: str) -> dict:
    """Devolve a procedência (nível, fontes, justificativa) de uma causa-raiz.

    Nunca levanta KeyError: chaves não catalogadas devolvem nível estimativa,
    lista de fontes vazia e uma justificativa genérica.
    """
    return _procedencia(FUNDAMENTACAO_CAUSAS, nome_causa)


def procedencia_modificador(chave: str) -> dict:
    """Devolve a procedência (nível, fontes, justificativa) de um modificador
    contextual de MotorCausaRaiz.MODIFICADORES.

    Nunca levanta KeyError: chaves não catalogadas devolvem nível estimativa,
    lista de fontes vazia e uma justificativa genérica.
    """
    return _procedencia(FUNDAMENTACAO_MODIFICADORES, chave)
