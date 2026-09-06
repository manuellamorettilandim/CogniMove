"""
Testes Unitários — Utilitários de Dados do Dashboard (Módulo 4)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from frontend.utils_dashboard import obter_causa_predominante


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
