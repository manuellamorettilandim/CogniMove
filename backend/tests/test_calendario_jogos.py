"""
Testes Unitários — Calendário de Jogos do Brasileirão (openfootball)

Cobre o parser puro do formato de texto e a busca de jogos por data/time,
incluindo o caso de normalização de acentos ("São Paulo" x "Sao Paulo").
Todos os testes rodam sem rede.
"""
from __future__ import annotations

import datetime
from unittest.mock import patch

import pytest

from backend.analytics.calendario_jogos import (
    carregar_texto_calendario,
    jogo_na_data,
    parse_calendario,
)

TRECHO_EXEMPLO = """\
▪ Matchday 1
  Wed Jan 28 2026
    19:00  CA Mineiro              v SE Palmeiras             2-2 (1-1)
           Coritiba FBC            v RB Bragantino            0-1 (0-0)
    20:00  Chapecoense AF          v Santos FC                4-2 (1-1)
  Thu Jan 29
    20:00  Mirassol FC             v CR Vasco da Gama         2-1 (1-1)
"""


def test_parse_calendario_datas_e_confrontos_com_heranca_de_ano():
    """Cenário (a): parse do trecho de exemplo devolve as datas e confrontos certos,
    incluindo a herança do ano de 2026 na segunda data ("Thu Jan 29"), que não repete o ano."""
    calendario = parse_calendario(TRECHO_EXEMPLO)

    assert calendario[datetime.date(2026, 1, 28)] == [
        ("CA Mineiro", "SE Palmeiras"),
        ("Coritiba FBC", "RB Bragantino"),
        ("Chapecoense AF", "Santos FC"),
    ]
    assert calendario[datetime.date(2026, 1, 29)] == [
        ("Mirassol FC", "CR Vasco da Gama"),
    ]


def test_parse_calendario_ignora_matchday_e_linhas_em_branco():
    """Cenário (b): linhas "▪ Matchday" e linhas em branco não geram entradas nem erros."""
    texto = """

▪ Matchday 1
  Wed Jan 28 2026

    19:00  CA Mineiro              v SE Palmeiras             2-2 (1-1)

▪ Matchday 2

"""
    calendario = parse_calendario(texto)
    assert len(calendario) == 1
    assert calendario[datetime.date(2026, 1, 28)] == [("CA Mineiro", "SE Palmeiras")]


def test_jogo_na_data_encontra_sao_paulo_com_acentuacao_diferente():
    """Cenário (c): "São Paulo FC" no calendário casa com o parâmetro "Sao Paulo" (sem acento)."""
    texto = (
        "▪ Matchday 1\n"
        "  Wed Jan 28 2026\n"
        "    19:00  São Paulo FC            v CR Flamengo              2-1 (0-0)\n"
    )
    with patch(
        "backend.analytics.calendario_jogos.carregar_texto_calendario",
        return_value=texto,
    ):
        jogo, confronto = jogo_na_data(datetime.date(2026, 1, 28))

    assert jogo is True
    assert confronto == "São Paulo FC x CR Flamengo"


def test_jogo_na_data_sem_jogo_dos_times_monitorados():
    """Cenário (d): data sem nenhum dos times monitorados retorna (False, None)."""
    texto = (
        "▪ Matchday 1\n"
        "  Wed Jan 28 2026\n"
        "    19:00  Coritiba FBC            v RB Bragantino            0-1 (0-0)\n"
    )
    with patch(
        "backend.analytics.calendario_jogos.carregar_texto_calendario",
        return_value=texto,
    ):
        jogo, confronto = jogo_na_data(datetime.date(2026, 1, 28))

    assert jogo is False
    assert confronto is None


def test_carregar_texto_calendario_cai_na_copia_local_quando_rede_falha():
    """Cenário (e): se requests.get falhar, cai para a leitura da cópia local sem propagar exceção."""
    with patch(
        "backend.analytics.calendario_jogos.requests.get",
        side_effect=Exception("timeout"),
    ), patch(
        "backend.analytics.calendario_jogos.CAMINHO_LOCAL"
    ) as caminho_mock:
        caminho_mock.read_text.return_value = "conteudo local de teste"
        texto = carregar_texto_calendario()

    assert texto == "conteudo local de teste"
