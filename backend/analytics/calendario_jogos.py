"""
CogniMove — Calendário de Jogos do Brasileirão (Módulo 3)

Fonte de dados: projeto openfootball (domínio público, sem chave de API),
mantido no GitHub em formato texto simples:
  https://raw.githubusercontent.com/openfootball/south-america/master/brazil/2026_br1.txt

Substitui a integração anterior com TheSportsDB, cuja chave de teste
gratuita sempre devolvia a mesma resposta de exemplo (jogos de beisebol de
2014), tornando impossível confirmar jogos reais.

Como o arquivo do openfootball é parcial (só traz rodadas já realizadas) e
a fonte remota pode ficar indisponível, mantemos uma cópia local em
`backend/analytics/dados/brasileirao_2026.txt` como fallback offline.
"""
from __future__ import annotations

import datetime
import logging
import re
import unicodedata
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

URL_CALENDARIO = (
    "https://raw.githubusercontent.com/openfootball/south-america/"
    "master/brazil/2026_br1.txt"
)
CAMINHO_LOCAL = Path(__file__).resolve().parent / "dados" / "brasileirao_2026.txt"
TIMEOUT_PADRAO = 5

_MESES = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

_RE_DATA = re.compile(
    r'^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Za-z]{3})\s+(\d{1,2})(?:\s+(\d{4}))?$'
)
_RE_HORA_PREFIXO = re.compile(r'^(\d{1,2}:\d{2})\s+(.*)$')
_RE_PLACAR = re.compile(r'\s+\d+-\d+.*$')


def parse_calendario(texto: str) -> dict[datetime.date, list[tuple[str, str]]]:
    """Converte o texto do calendário do openfootball em um dicionário data -> jogos.

    Função pura (sem rede). Regras do formato:
      - Linhas "▪ Matchday N" são ignoradas.
      - Linhas de data ("Wed Jan 28 2026") trazem o ano apenas quando ele muda
        em relação à última data lida; nas demais, o ano é herdado.
      - Linhas de jogo têm um horário opcional no início (omitido quando o
        jogo é no mesmo horário do anterior) e usam " v " para separar
        mandante e visitante, seguido do placar (descartado).
    """
    calendario: dict[datetime.date, list[tuple[str, str]]] = {}
    data_atual: datetime.date | None = None
    ano_atual: int | None = None

    for linha_bruta in texto.splitlines():
        linha = linha_bruta.strip()
        if not linha or linha.startswith("▪") or linha.startswith("=") or linha.startswith("#"):
            continue

        m_data = _RE_DATA.match(linha)
        if m_data:
            mes_str, dia_str, ano_str = m_data.groups()
            if ano_str:
                ano_atual = int(ano_str)
            if ano_atual is None:
                continue
            data_atual = datetime.date(ano_atual, _MESES[mes_str], int(dia_str))
            continue

        if " v " not in linha or data_atual is None:
            continue

        m_hora = _RE_HORA_PREFIXO.match(linha)
        resto = m_hora.group(2) if m_hora else linha
        if " v " not in resto:
            continue

        mandante_bruto, visitante_bruto = resto.split(" v ", 1)
        mandante = mandante_bruto.strip()
        visitante = _RE_PLACAR.sub("", visitante_bruto).strip()
        if mandante and visitante:
            calendario.setdefault(data_atual, []).append((mandante, visitante))

    return calendario


def carregar_texto_calendario(usar_rede: bool = True) -> str:
    """Obtém o texto bruto do calendário: rede primeiro, cópia local como fallback.

    Nunca levanta exceção: qualquer falha (rede ou leitura local) é logada
    como aviso e, se as duas fontes falharem, devolve string vazia.
    """
    if usar_rede:
        try:
            resp = requests.get(URL_CALENDARIO, timeout=TIMEOUT_PADRAO)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.warning(
                "Falha ao baixar calendário do Brasileirão (openfootball): %s. "
                "Usando cópia local.", e,
            )

    try:
        return CAMINHO_LOCAL.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(
            "Falha ao ler cópia local do calendário (%s): %s", CAMINHO_LOCAL, e,
        )
        return ""


def _normalizar(texto: str) -> str:
    """Remove acentos (NFKD + descarte de combining characters) e baixa a caixa."""
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(c for c in decomposto if not unicodedata.combining(c))
    return sem_acentos.lower()


def jogo_na_data(
    data: datetime.date,
    times: tuple[str, ...] = ("Corinthians", "Palmeiras", "Sao Paulo", "Santos"),
) -> tuple[bool, str | None]:
    """Verifica se algum dos times monitorados joga na data informada.

    Retorna (True, "Mandante x Visitante") no primeiro confronto encontrado,
    ou (False, None) se nenhum time monitorado jogar na data.
    """
    texto = carregar_texto_calendario()
    calendario = parse_calendario(texto)
    jogos_do_dia = calendario.get(data, [])

    times_normalizados = [_normalizar(t) for t in times]
    for mandante, visitante in jogos_do_dia:
        mandante_norm = _normalizar(mandante)
        visitante_norm = _normalizar(visitante)
        for time_norm in times_normalizados:
            if time_norm in mandante_norm or time_norm in visitante_norm:
                return True, f"{mandante} x {visitante}"

    return False, None
