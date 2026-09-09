"""
Testes unitários para utilitários de transparência e diagnóstico do Dashboard Streamlit.
"""
import pytest

from frontend.utils_dashboard import (
    formatar_selo_procedencia,
    formatar_contrafactual_diagnostico,
    montar_tabela_procedencia_causas,
    montar_resumo_contribuicoes,
    extrair_procedencia_segura,
)


def test_formatar_selo_procedencia_primaria():
    dados = {
        "nivel": "fonte_primaria",
        "fontes": [{"codigo": "NT 195/96", "orgao": "CET-SP", "titulo": "Chuva"}],
    }
    selo = formatar_selo_procedencia(dados)
    assert selo == "🟢 Fonte primária (NT 195/96 CET-SP)"


def test_formatar_selo_procedencia_secundaria():
    dados = {
        "nivel": "fonte_secundaria",
        "fontes": [{"codigo": None, "orgao": "Instituto de Engenharia", "titulo": "Sinalização"}],
    }
    selo = formatar_selo_procedencia(dados)
    assert selo == "🟡 Fonte secundária (Instituto de Engenharia)"


def test_formatar_selo_procedencia_estimativa():
    dados = {
        "nivel": "estimativa_equipe",
        "fontes": [],
    }
    selo = formatar_selo_procedencia(dados)
    assert selo == "⚪ Estimativa da equipe"


def test_formatar_selo_procedencia_invalido_ou_nulo():
    assert formatar_selo_procedencia(None) == "⚪ Estimativa da equipe"
    assert formatar_selo_procedencia({}) == "⚪ Estimativa da equipe"
    assert formatar_selo_procedencia("invalido") == "⚪ Estimativa da equipe"


def test_formatar_contrafactual_diagnostico_mudou_causa():
    resultado_cf = {
        "real": {
            "causa_principal": "Sinalização pouco visível",
            "confianca": 0.42,
            "fatores_ativos": ["Chuva Forte / Baixa Visibilidade"],
        },
        "neutro": {
            "causa_principal": "Tempo semafórico inadequado",
            "confianca": 0.35,
            "fatores_ativos": [],
        },
        "mudou_causa": True,
    }
    diag = formatar_contrafactual_diagnostico(resultado_cf)
    assert diag["mostrar_neutra"] is True
    assert diag["linha_real"] == "Com [Chuva Forte / Baixa Visibilidade]: Sinalização pouco visível — 42%"
    assert diag["linha_neutra"] == "Sem nenhum fator ativo seria: Tempo semafórico inadequado — 35%"


def test_formatar_contrafactual_diagnostico_mesma_causa_diff_grande():
    resultado_cf = {
        "real": {
            "causa_principal": "Tempo semafórico inadequado",
            "confianca": 0.50,
            "fatores_ativos": ["Horário de Pico"],
        },
        "neutro": {
            "causa_principal": "Tempo semafórico inadequado",
            "confianca": 0.35,
            "fatores_ativos": [],
        },
        "mudou_causa": False,
    }
    diag = formatar_contrafactual_diagnostico(resultado_cf, limiar_diferenca_pct=5.0)
    assert diag["mostrar_neutra"] is True
    assert diag["linha_real"] == "Com [Horário de Pico]: Tempo semafórico inadequado — 50%"
    assert diag["linha_neutra"] == "Sem nenhum fator ativo seria: Tempo semafórico inadequado — 35%"


def test_formatar_contrafactual_diagnostico_mesma_causa_diff_pequena_omite_neutra():
    resultado_cf = {
        "real": {
            "causa_principal": "Tempo semafórico inadequado",
            "confianca": 0.36,
            "fatores_ativos": ["Horário de Pico"],
        },
        "neutro": {
            "causa_principal": "Tempo semafórico inadequado",
            "confianca": 0.35,
            "fatores_ativos": [],
        },
        "mudou_causa": False,
    }
    diag = formatar_contrafactual_diagnostico(resultado_cf, limiar_diferenca_pct=5.0)
    assert diag["mostrar_neutra"] is False
    assert diag["linha_neutra"] is None
    assert diag["linha_real"] == "Com [Horário de Pico]: Tempo semafórico inadequado — 36%"


def test_montar_tabela_procedencia_causas():
    resultado_causa = {
        "distribuicao": {
            "Tempo semafórico inadequado": 0.45,
            "Sinalização pouco visível": 0.30,
        },
        "distribuicao_base": {
            "Tempo semafórico inadequado": 0.35,
            "Sinalização pouco visível": 0.15,
        },
    }
    tab = montar_tabela_procedencia_causas(resultado_causa)
    assert len(tab) == 2
    assert tab[0]["Causa-Raiz"] == "Tempo semafórico inadequado"
    assert tab[0]["Probabilidade Final"] == "45.0%"
    assert "🟢" in tab[0]["Procedência Técnica"]
    assert tab[1]["Causa-Raiz"] == "Sinalização pouco visível"
    assert "🟡" in tab[1]["Procedência Técnica"]


def test_montar_resumo_contribuicoes():
    resultado_causa = {
        "contribuicoes": [
            ("contexto", "Sinalização pouco visível", 0.25),
            ("evidencia", "Tempo semafórico inadequado", 0.10),
        ]
    }
    contexto = {"chuva_forte": True, "horario_pico": False}
    resumo = montar_resumo_contribuicoes(resultado_causa, contexto)
    assert len(resumo["contexto"]) == 1
    assert resumo["contexto"][0]["causa"] == "Sinalização pouco visível"
    assert resumo["contexto"][0]["pontos_formatado"] == "+25 pts"
    assert len(resumo["evidencia"]) == 1
    assert resumo["evidencia"][0]["causa"] == "Tempo semafórico inadequado"
    assert len(resumo["modificadores_ativos"]) == 1
    assert resumo["modificadores_ativos"][0]["chave"] == "chuva_forte"
    assert "🟢" in resumo["modificadores_ativos"][0]["selo"]


def test_extrair_procedencia_segura():
    proc = extrair_procedencia_segura("Tempo semafórico inadequado", tipo="causa")
    assert proc["nivel"] == "fonte_primaria"

    proc_inexistente = extrair_procedencia_segura("Causa Estranha Inexistente", tipo="causa")
    assert proc_inexistente["nivel"] == "estimativa_equipe"
