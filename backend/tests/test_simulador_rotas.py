"""
Testes Unitários — Rotas Flask do Simulador de Câmera

Valida o tratamento de erros das rotas novas em frontend/app.py, sem
depender de rede real (as integrações de contexto e o relatório em
disco são mockados).
"""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from frontend.app import app, _simulador_estado, _simulador_lock


@pytest.fixture(autouse=True)
def limpar_estado_simulador():
    """Garante que cada teste comece sem sessão de simulação ativa."""
    with _simulador_lock:
        _simulador_estado["contexto"] = None
        _simulador_estado["motor"] = None
        _simulador_estado["relatorio"] = None
    yield
    with _simulador_lock:
        _simulador_estado["contexto"] = None
        _simulador_estado["motor"] = None
        _simulador_estado["relatorio"] = None


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_infracao_sem_iniciar_retorna_400(client):
    """POST /api/simulador/infracao antes de /api/simulador/iniciar deve retornar 400, não uma exceção."""
    resp = client.post("/api/simulador/infracao", json={"tipo": "AVANCO_SINAL_VERMELHO"})
    assert resp.status_code == 400
    assert "erro" in resp.get_json()


def test_infracao_tipo_invalido_retorna_400(client):
    """Tipo de infração fora dos 3 válidos deve retornar 400."""
    resp = client.post("/api/simulador/infracao", json={"tipo": "TIPO_INEXISTENTE"})
    assert resp.status_code == 400


def test_iniciar_sem_data_ou_hora_retorna_400(client):
    """Campos 'data'/'hora' ausentes devem retornar 400 claro."""
    resp = client.post("/api/simulador/iniciar", json={})
    assert resp.status_code == 400


def test_iniciar_com_data_invalida_retorna_400(client):
    """Formato inválido de data/hora deve retornar 400, não uma exceção."""
    resp = client.post("/api/simulador/iniciar", json={"data": "not-a-date", "hora": "18:30"})
    assert resp.status_code == 400


def test_fluxo_iniciar_e_registrar_infracao(client):
    """Fluxo feliz: inicia a sessão (mockada) e depois registra uma infração."""
    contexto_fake = {
        "chuva_forte": True, "dia_jogo": False, "horario_pico": True,
        "feriado": False, "obra_viaria": False,
        "fatores_ativos": ["Chuva Forte / Baixa Visibilidade", "Horário de Pico"],
        "_detalhes": {"precipitacao_mm": 4.2, "confronto": None},
    }

    relatorio_mock = MagicMock()

    with patch(
        "backend.analytics.contexto_tempo_real.construir_contexto_a_partir_de_data",
        return_value=contexto_fake,
    ), patch("infracoes.relatorio.GerenciadorRelatorio", return_value=relatorio_mock):
        resp_iniciar = client.post(
            "/api/simulador/iniciar",
            json={"data": "2026-03-10", "hora": "18:30", "obra_viaria": False},
        )
        assert resp_iniciar.status_code == 200
        assert resp_iniciar.get_json()["chuva_forte"] is True

        resp_infracao = client.post(
            "/api/simulador/infracao", json={"tipo": "BLOQUEIO_CRUZAMENTO"},
        )

    assert resp_infracao.status_code == 200
    dados = resp_infracao.get_json()
    assert "causa_principal" in dados
    assert "confianca" in dados
    assert "distribuicao" in dados
    relatorio_mock.adicionar.assert_called_once()
