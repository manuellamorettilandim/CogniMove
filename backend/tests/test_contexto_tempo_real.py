"""
Testes Unitários — Contexto Urbano em Tempo Real (Simulador de Câmera)

Valida as 4 funções de integração de dados reais e o comportamento de
fallback quando uma API externa falha (timeout, erro de rede etc.).
"""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.analytics.contexto_tempo_real import (
    verificar_feriado,
    verificar_chuva_forte,
    verificar_dia_de_jogo,
    verificar_horario_pico,
    construir_contexto_a_partir_de_data,
)


# ── verificar_horario_pico ────────────────────────────────────────────────

def test_horario_pico_fim_de_semana_sempre_false():
    """Fins de semana (sábado=5, domingo=6) nunca contam como horário de pico."""
    assert verificar_horario_pico(datetime.time(8, 0), 5) is False
    assert verificar_horario_pico(datetime.time(18, 0), 6) is False


def test_horario_pico_dia_de_semana_dentro_do_pico():
    """Manhã e tarde dentro das janelas de pico em dia de semana retornam True."""
    assert verificar_horario_pico(datetime.time(7, 30), 0) is True
    assert verificar_horario_pico(datetime.time(18, 0), 2) is True


def test_horario_pico_dia_de_semana_fora_do_pico():
    """Horário fora das janelas de pico em dia de semana retorna False."""
    assert verificar_horario_pico(datetime.time(12, 0), 1) is False
    assert verificar_horario_pico(datetime.time(23, 0), 3) is False


# ── verificar_feriado ──────────────────────────────────────────────────────

def test_verificar_feriado_data_conhecida():
    """1º de Janeiro é feriado nacional em qualquer ano."""
    assert verificar_feriado(datetime.date(2026, 1, 1)) is True


def test_verificar_feriado_data_comum():
    """Uma data qualquer sem feriado conhecido retorna False."""
    assert verificar_feriado(datetime.date(2026, 3, 10)) is False


# ── verificar_chuva_forte ──────────────────────────────────────────────────

def test_verificar_chuva_forte_sucesso():
    """Consulta bem-sucedida retorna (True, mm) quando precipitação >= limiar."""
    data = datetime.date(2026, 1, 15)
    hora = datetime.time(14, 0)
    resposta_mock = MagicMock()
    resposta_mock.raise_for_status.return_value = None
    resposta_mock.json.return_value = {
        "hourly": {
            "time": ["2026-01-15T14:00"],
            "precipitation": [5.0],
        }
    }
    with patch("backend.analytics.contexto_tempo_real.requests.get", return_value=resposta_mock):
        chuva, mm = verificar_chuva_forte(data, hora)
    assert chuva is True
    assert mm == 5.0


def test_verificar_chuva_forte_falha_de_rede_retorna_fallback():
    """Se requests.get lançar exceção, retorna (False, 0.0) sem propagar."""
    data = datetime.date(2026, 1, 15)
    hora = datetime.time(14, 0)
    with patch("backend.analytics.contexto_tempo_real.requests.get", side_effect=Exception("timeout")):
        chuva, mm = verificar_chuva_forte(data, hora)
    assert chuva is False
    assert mm == 0.0


# ── verificar_dia_de_jogo ───────────────────────────────────────────────────

def test_verificar_dia_de_jogo_encontrado():
    """Retorna (True, confronto) quando um dos times monitorados joga na data."""
    resposta_mock = MagicMock()
    resposta_mock.raise_for_status.return_value = None
    resposta_mock.json.return_value = {
        "events": [{"strHomeTeam": "Palmeiras", "strAwayTeam": "Corinthians"}]
    }
    with patch("backend.analytics.contexto_tempo_real.requests.get", return_value=resposta_mock):
        jogo, confronto = verificar_dia_de_jogo(datetime.date(2026, 3, 10))
    assert jogo is True
    assert confronto == "Palmeiras x Corinthians"


def test_verificar_dia_de_jogo_falha_de_rede_retorna_fallback():
    """Se requests.get lançar exceção, retorna (False, None) sem propagar."""
    with patch("backend.analytics.contexto_tempo_real.requests.get", side_effect=Exception("timeout")):
        jogo, confronto = verificar_dia_de_jogo(datetime.date(2026, 3, 10))
    assert jogo is False
    assert confronto is None


# ── construir_contexto_a_partir_de_data ─────────────────────────────────────

def test_construir_contexto_a_partir_de_data_integra_fatores():
    """A função orquestradora combina os 4 fatores no formato de GerenciadorContextoUrbano."""
    with patch("backend.analytics.contexto_tempo_real.verificar_feriado", return_value=True), \
         patch("backend.analytics.contexto_tempo_real.verificar_chuva_forte", return_value=(True, 8.0)), \
         patch("backend.analytics.contexto_tempo_real.verificar_dia_de_jogo", return_value=(False, None)):
        contexto = construir_contexto_a_partir_de_data(
            datetime.date(2026, 1, 1), datetime.time(18, 30), obra_viaria_manual=True,
        )

    assert contexto["feriado"] is True
    assert contexto["chuva_forte"] is True
    assert contexto["obra_viaria"] is True
    assert contexto["dia_jogo"] is False
    assert contexto["_detalhes"]["precipitacao_mm"] == 8.0
    assert "fatores_ativos" in contexto
