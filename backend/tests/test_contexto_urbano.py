"""
Testes Unitários — Módulo de Contexto Urbano (Módulo 3)

Testes de integridade, setters, getters e concorrência / thread-safety.
"""
from __future__ import annotations

import threading
import pytest
from backend.analytics.contexto_urbano import GerenciadorContextoUrbano


def test_contexto_inicial_desligado():
    """Valida se o estado inicial do contexto urbano começa com todos os fatores desativados."""
    gerenciador = GerenciadorContextoUrbano()
    ctx = gerenciador.obter_contexto_atual()

    assert ctx["chuva_forte"] is False
    assert ctx["dia_jogo"] is False
    assert ctx["horario_pico"] is False
    assert ctx["feriado"] is False
    assert ctx["obra_viaria"] is False
    assert ctx["fatores_ativos"] == []
    assert "timestamp" in ctx


def test_setters_individuais():
    """Valida se cada setter altera individualmente o estado do contexto e lista os fatores ativos."""
    gerenciador = GerenciadorContextoUrbano()

    gerenciador.set_chuva_forte(True)
    ctx = gerenciador.obter_contexto_atual()
    assert ctx["chuva_forte"] is True
    assert "Chuva Forte / Baixa Visibilidade" in ctx["fatores_ativos"]

    gerenciador.set_horario_pico(True)
    ctx = gerenciador.obter_contexto_atual()
    assert ctx["horario_pico"] is True
    assert "Horário de Pico" in ctx["fatores_ativos"]
    assert len(ctx["fatores_ativos"]) == 2

    gerenciador.set_chuva_forte(False)
    ctx = gerenciador.obter_contexto_atual()
    assert ctx["chuva_forte"] is False
    assert "Chuva Forte / Baixa Visibilidade" not in ctx["fatores_ativos"]
    assert len(ctx["fatores_ativos"]) == 1


def test_atualizar_contexto_em_lote():
    """Valida o método atualizar_contexto() que altera múltiplos estados simultaneamente."""
    gerenciador = GerenciadorContextoUrbano()
    gerenciador.atualizar_contexto(
        chuva_forte=True,
        dia_jogo=True,
        horario_pico=False,
        feriado=False,
        obra_viaria=True,
    )
    ctx = gerenciador.obter_contexto_atual()

    assert ctx["chuva_forte"] is True
    assert ctx["dia_jogo"] is True
    assert ctx["horario_pico"] is False
    assert ctx["feriado"] is False
    assert ctx["obra_viaria"] is True
    assert len(ctx["fatores_ativos"]) == 3


def test_set_flag_generico():
    """Valida o método genérico set_flag(nome, estado)."""
    gerenciador = GerenciadorContextoUrbano()

    gerenciador.set_flag("dia_jogo", True)
    assert gerenciador.obter_contexto_atual()["dia_jogo"] is True

    gerenciador.set_flag("dia_jogo", False)
    assert gerenciador.obter_contexto_atual()["dia_jogo"] is False


def test_set_flag_invalido_lanca_keyerror():
    """Valida que set_flag levanta KeyError ao receber um nome de cenário desconhecido."""
    gerenciador = GerenciadorContextoUrbano()
    with pytest.raises(KeyError) as excinfo:
        gerenciador.set_flag("cenario_inexistente", True)

    assert "Cenário urbano desconhecido" in str(excinfo.value)


def test_contexto_urbano_thread_safe():
    """
    (2.e) Instancia GerenciadorContextoUrbano, dispara múltiplas threads chamando
    setters e getters concorrentemente e valida que obter_contexto_atual() nunca lança
    exceção e sempre retorna um dict consistente com todas as chaves esperadas.
    """
    gerenciador = GerenciadorContextoUrbano()
    erros = []
    chaves_esperadas = {
        "chuva_forte",
        "dia_jogo",
        "horario_pico",
        "feriado",
        "obra_viaria",
        "timestamp",
        "fatores_ativos",
    }

    def worker_setters(thread_id: int):
        for i in range(200):
            try:
                estado = (i % 2 == 0)
                if thread_id % 5 == 0:
                    gerenciador.set_chuva_forte(estado)
                elif thread_id % 5 == 1:
                    gerenciador.set_dia_jogo(estado)
                elif thread_id % 5 == 2:
                    gerenciador.set_horario_pico(estado)
                elif thread_id % 5 == 3:
                    gerenciador.set_feriado(estado)
                else:
                    gerenciador.set_obra_viaria(estado)
            except Exception as e:
                erros.append(f"Erro em worker_setters (thread {thread_id}): {e}")

    def worker_getters(thread_id: int):
        for _ in range(200):
            try:
                ctx = gerenciador.obter_contexto_atual()
                if not isinstance(ctx, dict):
                    erros.append(f"Retorno não é dict: {type(ctx)}")
                if not chaves_esperadas.issubset(ctx.keys()):
                    erros.append(f"Chaves faltantes: {chaves_esperadas - set(ctx.keys())}")
                if not isinstance(ctx["fatores_ativos"], list):
                    erros.append("fatores_ativos não é list")
            except Exception as e:
                erros.append(f"Erro em worker_getters (thread {thread_id}): {e}")

    threads = []
    # Criar 10 threads de escrita e 10 threads de leitura simultâneas
    for t_id in range(10):
        threads.append(threading.Thread(target=worker_setters, args=(t_id,)))
        threads.append(threading.Thread(target=worker_getters, args=(t_id,)))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(erros) == 0, f"Erros durante execução concorrente: {erros}"
