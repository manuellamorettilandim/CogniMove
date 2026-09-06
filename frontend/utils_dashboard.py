"""
CogniMove — Utilitários de Tratamento e Extração de Dados do Dashboard
"""
from __future__ import annotations

import pandas as pd


def obter_causa_predominante(
    df: pd.DataFrame,
    coluna: str = "causa_principal",
    default: str = "N/A",
) -> str:
    """Retorna o valor mais frequente da coluna, ou `default` se não houver valores válidos."""
    if coluna not in df.columns:
        return default
    moda = df[coluna].mode()
    return str(moda.iloc[0]) if not moda.empty else default
