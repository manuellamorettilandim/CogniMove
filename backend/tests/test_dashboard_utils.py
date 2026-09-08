"""
Testes Unitários — Utilitários de Dados do Dashboard (Módulo 4)
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import pytest

from frontend.utils_dashboard import (
    coletar_avisos,
    obter_causa_predominante,
    resumir_contexto,
    traduzir_avisos_contexto,
)


def test_obter_causa_predominante_valores_normais():
    """Cenário (a): DataFrame com valores normais retorna o valor mais frequente."""
    df = pd.DataFrame({
        "causa_principal": [
            "Tempo semafórico inadequado",
            "Congestionamento",
            "Tempo semafórico inadequado",
            "Conduta do condutor",
        ]
    })
    resultado = obter_causa_predominante(df, default="N/A")
    assert resultado == "Tempo semafórico inadequado"


def test_obter_causa_predominante_apenas_nan():
    """Cenário (b): DataFrame onde a coluna só possui NaN/None retorna o default sem lançar exceção."""
    df = pd.DataFrame({
        "causa_principal": [np.nan, None, np.nan]
    })
    resultado = obter_causa_predominante(df, default="N/A")
    assert resultado == "N/A"

    resultado_vazio = obter_causa_predominante(df, default="")
    assert resultado_vazio == ""


def test_obter_causa_predominante_dataframe_vazio():
    """Cenário (c): DataFrame vazio (sem linhas) retorna o default sem lançar exceção."""
    df_vazio_com_coluna = pd.DataFrame(columns=["causa_principal"])
    assert obter_causa_predominante(df_vazio_com_coluna, default="N/A") == "N/A"
    assert obter_causa_predominante(df_vazio_com_coluna, default="") == ""

    df_totalmente_vazio = pd.DataFrame()
    assert obter_causa_predominante(df_totalmente_vazio, default="N/A") == "N/A"


def test_obter_causa_predominante_coluna_inexistente():
    """Valida se uma coluna não presente no DataFrame retorna o default com segurança."""
    df = pd.DataFrame({"outra_coluna": [1, 2, 3]})
    assert obter_causa_predominante(df, coluna="causa_principal", default="N/A") == "N/A"


def test_resumir_contexto_none():
    """Cenário (a): contexto None devolve a mensagem de contexto não consultado."""
    assert resumir_contexto(None) == "Contexto ainda não consultado."


def test_resumir_contexto_sem_fatores_ativos():
    """Cenário (b): todos os fatores desligados devolve a mensagem de nenhum risco identificado."""
    contexto = {
        "chuva_forte": False,
        "dia_jogo": False,
        "horario_pico": False,
        "feriado": False,
        "obra_viaria": False,
        "_detalhes": {},
    }
    assert resumir_contexto(contexto) == "Nenhum fator de risco identificado."


def test_resumir_contexto_chuva_jogo_pico_ativos():
    """Cenário (c): chuva, jogo e horário de pico ativos aparecem na frase, mas feriado não."""
    contexto = {
        "chuva_forte": True,
        "dia_jogo": True,
        "horario_pico": True,
        "feriado": False,
        "obra_viaria": False,
        "_detalhes": {"precipitacao_mm": 4.2, "confronto": "Corinthians x Palmeiras"},
    }
    resultado = resumir_contexto(contexto)
    assert "4.2 mm/h" in resultado
    assert "Corinthians x Palmeiras" in resultado
    assert "Horário de pico" in resultado
    assert "Feriado" not in resultado


def test_resumir_contexto_sem_chave_detalhes():
    """Cenário (d): ausência da chave '_detalhes' não quebra e usa os valores padrão."""
    contexto = {
        "chuva_forte": True,
        "dia_jogo": True,
        "horario_pico": False,
        "feriado": False,
        "obra_viaria": False,
    }
    resultado = resumir_contexto(contexto)
    assert "0.0 mm/h" in resultado
    assert "Jogo na cidade" in resultado


def test_traduzir_avisos_contexto_open_meteo():
    """Cenário (a): mensagem citando Open-Meteo vira o aviso de clima não confirmado."""
    resultado = traduzir_avisos_contexto(["Falha ao consultar clima (Open-Meteo): timeout"])
    assert resultado == ["Não foi possível confirmar o clima — assumindo sem chuva."]


def test_traduzir_avisos_contexto_thesportsdb():
    """Cenário (b): mensagem citando TheSportsDB vira o aviso de jogo não confirmado."""
    resultado = traduzir_avisos_contexto(["Falha ao consultar jogos (TheSportsDB): timeout"])
    assert resultado == ["Não foi possível confirmar jogos na cidade — assumindo sem jogo."]


def test_traduzir_avisos_contexto_deduplica_e_repassa_desconhecida():
    """Cenário (c): mensagens duplicadas viram uma só e mensagens não reconhecidas mantêm o texto original com prefixo."""
    mensagens = [
        "Falha ao consultar clima (Open-Meteo): timeout",
        "Falha ao consultar clima (Open-Meteo): timeout",
        "Erro desconhecido em outra fonte",
    ]
    resultado = traduzir_avisos_contexto(mensagens)
    assert resultado == [
        "Não foi possível confirmar o clima — assumindo sem chuva.",
        "Fonte externa indisponível: Erro desconhecido em outra fonte",
    ]


def test_coletar_avisos_captura_apenas_durante_o_bloco():
    """Cenário (d): warnings emitidos dentro do bloco são capturados; o handler é removido ao sair."""
    logger = logging.getLogger("teste_coletar_avisos")

    with coletar_avisos("teste_coletar_avisos") as avisos:
        logger.warning("aviso dentro do bloco")

    assert avisos == ["aviso dentro do bloco"]

    logger.warning("aviso depois do bloco")
    assert avisos == ["aviso dentro do bloco"]
