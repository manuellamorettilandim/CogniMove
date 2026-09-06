"""
Testes Unitários — Motor de Causa-Raiz (Módulo 2)

Testes puramente unitários executáveis via pytest sem dependências de GPU,
câmera ou modelos de IA.
"""
from __future__ import annotations

import logging
import pytest
from backend.analytics.causa_raiz import (
    Causa,
    MotorCausaRaiz,
    validar_tabela_base,
    _validar_consistencia_modificadores,
)
from backend.analytics.contexto_urbano import GerenciadorContextoUrbano


@pytest.fixture
def motor():
    return MotorCausaRaiz()


@pytest.fixture
def contexto_vazio():
    return GerenciadorContextoUrbano().obter_contexto_atual()


def test_tabela_base_soma_um():
    """Valida diretamente que os pesos brutos em TABELA_PROBABILIDADES_BASE somam 1.0."""
    validar_tabela_base()


def test_tabela_base_soma_incorreta_rejeitada():
    """Valida se validar_tabela_base levanta AssertionError caso uma soma seja diferente de 1.0."""
    original = MotorCausaRaiz.TABELA_PROBABILIDADES_BASE.copy()
    try:
        # Clona o dicionário interno para injetar erro sem poluir outras entradas
        MotorCausaRaiz.TABELA_PROBABILIDADES_BASE = {
            k: v.copy() for k, v in original.items()
        }
        MotorCausaRaiz.TABELA_PROBABILIDADES_BASE["AVANCO_SINAL_VERMELHO"][Causa.CONGESTIONAMENTO.value] = 0.99
        with pytest.raises(AssertionError) as excinfo:
            validar_tabela_base()
        assert "TABELA_PROBABILIDADES_BASE['AVANCO_SINAL_VERMELHO'] soma" in str(excinfo.value)
    finally:
        MotorCausaRaiz.TABELA_PROBABILIDADES_BASE = original


def test_distribuicao_soma_um(motor, contexto_vazio):
    """
    (2.a) Para cada tipo_infracao em TABELA_PROBABILIDADES_BASE,
    chama calcular_probabilidades() com contexto vazio e valida que
    a soma das probabilidades da distribuição é igual a 1.0 (tolerância < 1e-9).
    """
    for tipo_infracao in MotorCausaRaiz.TABELA_PROBABILIDADES_BASE:
        res = motor.calcular_probabilidades(tipo_infracao, contexto_vazio)
        distribuicao = res["distribuicao"]
        soma = sum(distribuicao.values())
        assert abs(soma - 1.0) < 1e-9, (
            f"A soma das probabilidades para '{tipo_infracao}' deveria ser 1.0, mas foi {soma}."
        )


def test_distribuicao_soma_um_com_cenarios_ativos(motor):
    """Garante que a normalização mantém soma próxima de 1.0 (tolerância de arredondamento a 4 casas decimais)."""
    gerenciador = GerenciadorContextoUrbano()
    gerenciador.atualizar_contexto(
        chuva_forte=True,
        dia_jogo=True,
        horario_pico=True,
        feriado=True,
        obra_viaria=True,
    )
    ctx_todos = gerenciador.obter_contexto_atual()

    for tipo_infracao in MotorCausaRaiz.TABELA_PROBABILIDADES_BASE:
        res = motor.calcular_probabilidades(tipo_infracao, ctx_todos)
        soma = sum(res["distribuicao"].values())
        assert abs(soma - 1.0) < 1e-3, (
            f"A soma com cenários ativos para '{tipo_infracao}' deveria ser ~1.0, mas foi {soma}."
        )


def test_modificador_existe_na_base():
    """
    (2.b) Para cada (causa, incremento) em MODIFICADORES, valida que
    a causa aparece em pelo menos uma entrada de TABELA_PROBABILIDADES_BASE.
    Evita regressão de causas fantasmas/órfãs como 'Baixa visibilidade'.
    """
    causas_base = {
        causa
        for sub_tabela in MotorCausaRaiz.TABELA_PROBABILIDADES_BASE.values()
        for causa in sub_tabela.keys()
    }

    for cenario, ajustes in MotorCausaRaiz.MODIFICADORES.items():
        assert isinstance(ajustes, list), f"Modificador '{cenario}' deve ser uma lista de tuplas."
        for causa, incremento in ajustes:
            assert causa in causas_base, (
                f"Regressão detectada: O modificador '{cenario}' referencia a causa órfã '{causa}' "
                f"que não existe na TABELA_PROBABILIDADES_BASE."
            )
            assert incremento > 0.0, f"O incremento do modificador '{cenario}' deve ser positivo."


def test_contexto_aumenta_probabilidade_esperada(motor, contexto_vazio):
    """
    (2.c) Ativa um cenário por vez e valida que a probabilidade da causa associada
    é estritamente maior do que no resultado com contexto vazio.
    """
    # 1. Horário de pico -> aumenta Congestionamento
    infracao = "AVANCO_SINAL_VERMELHO"
    res_base = motor.calcular_probabilidades(infracao, contexto_vazio)
    prob_cong_base = res_base["distribuicao"][Causa.CONGESTIONAMENTO.value]

    ctx_pico = GerenciadorContextoUrbano()
    ctx_pico.set_horario_pico(True)
    res_pico = motor.calcular_probabilidades(infracao, ctx_pico.obter_contexto_atual())
    prob_cong_pico = res_pico["distribuicao"][Causa.CONGESTIONAMENTO.value]

    assert prob_cong_pico > prob_cong_base, (
        f"A probabilidade de '{Causa.CONGESTIONAMENTO.value}' deveria ter aumentado em horário de pico "
        f"(de {prob_cong_base} para {prob_cong_pico})."
    )

    # 2. Chuva forte -> aumenta Sinalização pouco visível e NÃO cria 'Baixa visibilidade'
    prob_sinal_base = res_base["distribuicao"][Causa.SINALIZACAO_POUCO_VISIVEL.value]
    ctx_chuva = GerenciadorContextoUrbano()
    ctx_chuva.set_chuva_forte(True)
    res_chuva = motor.calcular_probabilidades(infracao, ctx_chuva.obter_contexto_atual())
    prob_sinal_chuva = res_chuva["distribuicao"][Causa.SINALIZACAO_POUCO_VISIVEL.value]

    assert "Baixa visibilidade" not in res_chuva["distribuicao"]
    assert prob_sinal_chuva > prob_sinal_base, (
        f"A probabilidade de '{Causa.SINALIZACAO_POUCO_VISIVEL.value}' deveria ter aumentado com chuva "
        f"(de {prob_sinal_base} para {prob_sinal_chuva})."
    )

    # 3. Obra viária -> aumenta Sinalização pouco visível
    ctx_obra = GerenciadorContextoUrbano()
    ctx_obra.set_obra_viaria(True)
    res_obra = motor.calcular_probabilidades(infracao, ctx_obra.obter_contexto_atual())
    prob_sinal_obra = res_obra["distribuicao"][Causa.SINALIZACAO_POUCO_VISIVEL.value]

    assert prob_sinal_obra > prob_sinal_base

    # 4. Feriado -> aumenta Conduta do condutor
    prob_cond_base = res_base["distribuicao"][Causa.CONDUTA_DO_CONDUTOR.value]
    ctx_feriado = GerenciadorContextoUrbano()
    ctx_feriado.set_feriado(True)
    res_feriado = motor.calcular_probabilidades(infracao, ctx_feriado.obter_contexto_atual())
    prob_cond_feriado = res_feriado["distribuicao"][Causa.CONDUTA_DO_CONDUTOR.value]

    assert prob_cond_feriado > prob_cond_base


def test_tipo_infracao_desconhecido_retorna_confianca_zero(motor, caplog):
    """
    (2.d) Chama calcular_probabilidades('TIPO_INVALIDO', {}) e valida que
    retorna causa_principal='Desconhecida', confianca=0.0 e emite log de ERROR.
    """
    tipo_invalido = "TIPO_INVALIDO"
    with caplog.at_level(logging.ERROR):
        resultado = motor.calcular_probabilidades(tipo_invalido, {})

    assert resultado["causa_principal"] == "Desconhecida"
    assert resultado["confianca"] == 0.0
    assert resultado["distribuicao"] == {}
    assert any(
        record.levelno == logging.ERROR and tipo_invalido in record.message
        for record in caplog.records
    ), f"Log de nível ERROR contendo '{tipo_invalido}' era esperado."


def test_validacao_modulo_rejeita_causa_orfa():
    """Valida se a função de validação no import levanta AssertionError se uma causa for órfã."""
    copia_modificadores = MotorCausaRaiz.MODIFICADORES.copy()
    try:
        MotorCausaRaiz.MODIFICADORES["cenario_teste_invalido"] = [("Causa Totalmente Inexistente", 0.5)]
        with pytest.raises(AssertionError) as excinfo:
            _validar_consistencia_modificadores()
        assert "Causa órfã detectada" in str(excinfo.value)
    finally:
        MotorCausaRaiz.MODIFICADORES = copia_modificadores


def test_desempate_deterministico_em_probabilidades_iguais(motor):
    """
    Valida se em caso de empate exato entre probabilidades, o critério de desempate
    é determinístico (ordem alfabética) e independente da ordem de inserção no dicionário.
    """
    original_base = MotorCausaRaiz.TABELA_PROBABILIDADES_BASE.copy()
    try:
        # Ordem 1: Causa B antes de Causa A
        MotorCausaRaiz.TABELA_PROBABILIDADES_BASE = {
            "INFRACAO_TESTE_EMPATE": {
                "Causa B": 0.45,
                "Causa A": 0.45,
                "Causa C": 0.10,
            }
        }
        res1 = motor.calcular_probabilidades("INFRACAO_TESTE_EMPATE", {})

        # Ordem 2: Causa A antes de Causa B
        MotorCausaRaiz.TABELA_PROBABILIDADES_BASE = {
            "INFRACAO_TESTE_EMPATE": {
                "Causa A": 0.45,
                "Causa B": 0.45,
                "Causa C": 0.10,
            }
        }
        res2 = motor.calcular_probabilidades("INFRACAO_TESTE_EMPATE", {})

        # Ambos devem produzir rigorosamente o mesmo resultado determinístico
        assert res1["causa_principal"] == res2["causa_principal"] == "Causa B"
        assert res1["confianca"] == res2["confianca"] == 0.45
    finally:
        MotorCausaRaiz.TABELA_PROBABILIDADES_BASE = original_base
