"""
Testes Unitários — Fundamentação do Motor de Causa-Raiz (Módulo 2)

Testes puramente unitários executáveis via pytest sem dependências de GPU,
câmera ou modelos de IA.
"""
from __future__ import annotations

from backend.analytics.causa_raiz import MotorCausaRaiz
from backend.analytics.fundamentacao import (
    FONTES,
    FUNDAMENTACAO_CAUSAS,
    FUNDAMENTACAO_MODIFICADORES,
    NIVEL_PRIMARIA,
    NIVEL_ESTIMATIVA,
    procedencia_causa,
    procedencia_modificador,
)


def test_toda_causa_da_tabela_base_tem_fundamentacao():
    """Toda causa presente em TABELA_PROBABILIDADES_BASE tem entrada em FUNDAMENTACAO_CAUSAS."""
    causas_base = {
        causa
        for sub_tabela in MotorCausaRaiz.TABELA_PROBABILIDADES_BASE.values()
        for causa in sub_tabela.keys()
    }
    for causa in causas_base:
        assert causa in FUNDAMENTACAO_CAUSAS, f"Causa sem fundamentação: {causa!r}"


def test_todo_modificador_tem_fundamentacao():
    """Todo modificador de MotorCausaRaiz.MODIFICADORES tem entrada em FUNDAMENTACAO_MODIFICADORES."""
    for chave in MotorCausaRaiz.MODIFICADORES.keys():
        assert chave in FUNDAMENTACAO_MODIFICADORES, f"Modificador sem fundamentação: {chave!r}"


def test_toda_sigla_citada_existe_em_fontes():
    """Toda sigla referenciada em FUNDAMENTACAO_CAUSAS/FUNDAMENTACAO_MODIFICADORES existe em FONTES."""
    for entrada in list(FUNDAMENTACAO_CAUSAS.values()) + list(FUNDAMENTACAO_MODIFICADORES.values()):
        for sigla in entrada["fontes"]:
            assert sigla in FONTES, f"Sigla citada sem entrada em FONTES: {sigla!r}"


def test_procedencia_causa_chave_inexistente_nao_levanta_excecao():
    """procedencia_causa com chave inexistente devolve nível estimativa sem levantar exceção."""
    resultado = procedencia_causa("Causa que não existe")
    assert resultado["nivel"] == NIVEL_ESTIMATIVA
    assert resultado["fontes"] == []
    assert resultado["justificativa"]


def test_procedencia_modificador_chave_inexistente_nao_levanta_excecao():
    """procedencia_modificador com chave inexistente devolve nível estimativa sem levantar exceção."""
    resultado = procedencia_modificador("modificador_inexistente")
    assert resultado["nivel"] == NIVEL_ESTIMATIVA
    assert resultado["fontes"] == []
    assert resultado["justificativa"]


def test_procedencia_modificador_chuva_forte():
    """procedencia_modificador('chuva_forte') devolve nível primário e a fonte NT195 com url preenchida."""
    resultado = procedencia_modificador("chuva_forte")
    assert resultado["nivel"] == NIVEL_PRIMARIA
    assert len(resultado["fontes"]) == 1
    assert resultado["fontes"][0]["url"]
    assert resultado["fontes"][0] == FONTES["NT195"]
