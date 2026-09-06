"""
Testes Unitários — Recomendações Urbanas por Causa-Raiz (Módulo 4 / Dashboard)
"""
from __future__ import annotations

import pytest
from backend.analytics.causa_raiz import Causa
from frontend.recomendacoes import RECOMENDACOES_POR_CAUSA


def test_todas_causas_tem_recomendacao():
    """Valida se todos os membros do enum Causa possuem recomendação cadastrada."""
    causas_sem_recomendacao = [c for c in Causa if c.value not in RECOMENDACOES_POR_CAUSA]
    assert not causas_sem_recomendacao, (
        f"Causas sem recomendação cadastrada: {[c.value for c in causas_sem_recomendacao]}"
    )


def test_recomendacoes_sem_chaves_orfas():
    """Valida se não existem chaves no dicionário de recomendações que não pertençam ao enum Causa."""
    valores_causa = {c.value for c in Causa}
    chaves_orfas = [k for k in RECOMENDACOES_POR_CAUSA if k not in valores_causa]
    assert not chaves_orfas, f"Chaves órfãs encontradas em RECOMENDACOES_POR_CAUSA: {chaves_orfas}"
