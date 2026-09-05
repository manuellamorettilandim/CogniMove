"""
CogniMove — Smoke Test Manual de Analytics

ATENÇÃO: Este script serve apenas para validação rápida e manual no terminal.
Ele NÃO substitui a suíte de testes unitários formal localizada em:
  backend/tests/ (executável via `pytest backend/tests/`)
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd
import plotly
import streamlit as st

from backend.analytics.contexto_urbano import GerenciadorContextoUrbano
from backend.analytics.causa_raiz import Causa, MotorCausaRaiz


def test_causa_enum_members():
    """Valida se os membros do Enum Causa possuem os valores esperados."""
    esperados = {
        "TEMPO_SEMAFORICO_INADEQUADO": "Tempo semafórico inadequado",
        "CONGESTIONAMENTO": "Congestionamento",
        "CONDUTA_DO_CONDUTOR": "Conduta do condutor",
        "SINALIZACAO_POUCO_VISIVEL": "Sinalização pouco visível",
        "PINTURA_DESGASTADA_AUSENTE": "Pintura desgastada / ausente",
        "AUSENCIA_DE_SEGREGADOR_FISICO": "Ausência de segregador físico",
    }
    for nome, valor in esperados.items():
        assert hasattr(Causa, nome), f"Enum Causa não possui o membro {nome}"
        assert getattr(Causa, nome).value == valor, f"Valor incorreto para {nome}"
    print("[OK] Enum Causa validado com sucesso!")


def test_modificadores_sem_causas_orfas():
    """Valida que todas as causas em MODIFICADORES existem na base."""
    causas_base = {
        causa
        for sub_tabela in MotorCausaRaiz.TABELA_PROBABILIDADES_BASE.values()
        for causa in sub_tabela.keys()
    }
    for cenario, (causa, _) in MotorCausaRaiz.MODIFICADORES.items():
        assert causa in causas_base, f"Causa órfã '{causa}' encontrada em '{cenario}'"
    print("[OK] MODIFICADORES consistentes com TABELA_PROBABILIDADES_BASE!")


def test_validacao_detecta_causa_orfa():
    """Valida se uma causa órfã hipotética dispara AssertionError."""
    from backend.analytics.causa_raiz import _validar_consistencia_modificadores

    original = MotorCausaRaiz.MODIFICADORES.copy()
    try:
        MotorCausaRaiz.MODIFICADORES["cenario_invalido"] = ("Causa Que Nao Existe", 0.30)
        try:
            _validar_consistencia_modificadores()
            raise AssertionError("Deveria ter lançado AssertionError para causa órfã!")
        except AssertionError as e:
            assert "Causa órfã detectada" in str(e)
            print("[OK] Validação de causa órfã interceptou erro com sucesso:", e)
    finally:
        MotorCausaRaiz.MODIFICADORES = original


def test_chuva_forte_modificador():
    """
    Ativa apenas 'chuva_forte' no contexto, chama calcular_probabilidades()
    e verifica que:
    1. 'Baixa visibilidade' NÃO aparece na distribuição retornada.
    2. 'Sinalização pouco visível' teve sua probabilidade aumentada em relação
       ao caso sem contexto ativo.
    """
    motor = MotorCausaRaiz()
    infracao = "AVANCO_SINAL_VERMELHO"

    # Caso 1: Sem contexto ativo (neutro)
    ctx_neutro = GerenciadorContextoUrbano()
    res_neutro = motor.calcular_probabilidades(infracao, ctx_neutro.obter_contexto_atual())
    dist_neutro = res_neutro["distribuicao"]
    prob_sinal_neutro = dist_neutro[Causa.SINALIZACAO_POUCO_VISIVEL.value]

    # Caso 2: Apenas chuva_forte ativo
    ctx_chuva = GerenciadorContextoUrbano()
    ctx_chuva.set_chuva_forte(True)
    res_chuva = motor.calcular_probabilidades(infracao, ctx_chuva.obter_contexto_atual())
    dist_chuva = res_chuva["distribuicao"]

    print("Distribuição sem contexto:", dist_neutro)
    print("Distribuição com chuva forte:", dist_chuva)

    # Asserts obrigatórios da tarefa
    assert "Baixa visibilidade" not in dist_chuva, (
        "Erro: 'Baixa visibilidade' não deve aparecer na distribuição retornada!"
    )
    assert Causa.SINALIZACAO_POUCO_VISIVEL.value in dist_chuva, (
        f"Erro: '{Causa.SINALIZACAO_POUCO_VISIVEL.value}' deve estar presente na distribuição!"
    )

    prob_sinal_chuva = dist_chuva[Causa.SINALIZACAO_POUCO_VISIVEL.value]
    assert prob_sinal_chuva > prob_sinal_neutro, (
        f"Erro: Probabilidade de '{Causa.SINALIZACAO_POUCO_VISIVEL.value}' deveria ter aumentado "
        f"(de {prob_sinal_neutro} para {prob_sinal_chuva})"
    )

    # Verificar também para INVASAO_FAIXA
    res_faixa_neutro = motor.calcular_probabilidades("INVASAO_FAIXA", ctx_neutro.obter_contexto_atual())
    res_faixa_chuva = motor.calcular_probabilidades("INVASAO_FAIXA", ctx_chuva.obter_contexto_atual())
    assert "Baixa visibilidade" not in res_faixa_chuva["distribuicao"]
    assert (
        res_faixa_chuva["distribuicao"][Causa.SINALIZACAO_POUCO_VISIVEL.value]
        > res_faixa_neutro["distribuicao"][Causa.SINALIZACAO_POUCO_VISIVEL.value]
    )

    print(
        f"[OK] Teste chuva_forte passou com sucesso! "
        f"Probabilidade aumentou de {prob_sinal_neutro:.4f} para {prob_sinal_chuva:.4f} "
        f"e 'Baixa visibilidade' não foi gerada."
    )


def test_detector_fallback_warnings():
    """Valida se o construtor do InfracaoDetector emite warnings quando instanciado sem contexto ou motor."""
    import logging
    from backend.detection.infracoes.detector import InfracaoDetector

    detector_logger = logging.getLogger("backend.detection.infracoes.detector")
    mensagens_log = []

    class HandlerCaptura(logging.Handler):
        def emit(self, record):
            mensagens_log.append(record.getMessage())

    handler = HandlerCaptura()
    detector_logger.addHandler(handler)
    detector_logger.setLevel(logging.WARNING)

    try:
        # Caso 1: Sem contexto_urbano e sem motor_causa_raiz
        d1 = InfracaoDetector(source=0, camera_name="Camera Teste 1")
        assert any("sem contexto_urbano compartilhado" in m for m in mensagens_log), (
            "Warning de contexto_urbano esperado"
        )
        assert any("sem motor_causa_raiz compartilhado" in m for m in mensagens_log), (
            "Warning de motor_causa_raiz esperado"
        )
        assert d1.contexto_urbano is not None
        assert d1.motor_causa_raiz is not None

        # Caso 2: Com ambos passados explicitamente (nenhum warning emitido)
        mensagens_log.clear()
        ctx = GerenciadorContextoUrbano()
        mot = MotorCausaRaiz()
        d2 = InfracaoDetector(
            source=0,
            camera_name="Camera Teste 2",
            contexto_urbano=ctx,
            motor_causa_raiz=mot,
        )
        assert len(mensagens_log) == 0, (
            f"Nenhum warning deveria ser emitido quando instâncias são passadas, mas recebeu: {mensagens_log}"
        )
        assert d2.contexto_urbano is ctx
        assert d2.motor_causa_raiz is mot
        print("[OK] Teste de warnings no fallback do InfracaoDetector passou com sucesso!")
    finally:
        detector_logger.removeHandler(handler)


def test_tipo_infracao_nao_mapeado_emite_error(caplog=None):
    """Valida se uma infração não mapeada emite log ERROR contendo o tipo inválido."""
    import logging

    motor = MotorCausaRaiz()
    ctx = GerenciadorContextoUrbano().obter_contexto_atual()
    tipo_invalido = "TIPO_INEXISTENTE"

    if caplog is not None:
        with caplog.at_level(logging.ERROR):
            res = motor.calcular_probabilidades(tipo_invalido, ctx)
            assert res["causa_principal"] == "Desconhecida"
            assert res["confianca"] == 0.0
            assert res["distribuicao"] == {}
            assert any(
                record.levelno == logging.ERROR and tipo_invalido in record.message
                for record in caplog.records
            ), f"Mensagem ERROR contendo {tipo_invalido} esperada nos registros do caplog."
    else:
        mensagens_error = []

        class ErrorHandlerCaptura(logging.Handler):
            def emit(self, record):
                if record.levelno >= logging.ERROR:
                    mensagens_error.append(record.getMessage())

        handler = ErrorHandlerCaptura()
        causa_logger = logging.getLogger("backend.analytics.causa_raiz")
        causa_logger.addHandler(handler)
        causa_logger.setLevel(logging.ERROR)
        try:
            res = motor.calcular_probabilidades(tipo_invalido, ctx)
            assert res["causa_principal"] == "Desconhecida"
            assert res["confianca"] == 0.0
            assert res["distribuicao"] == {}
            assert any(
                tipo_invalido in m for m in mensagens_error
            ), f"Mensagem ERROR contendo {tipo_invalido} esperada nos logs."
        finally:
            causa_logger.removeHandler(handler)

    print("[OK] Teste de log ERROR para tipo de infração inválido passou com sucesso!")


if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print(f"Pandas: {pd.__version__} | Plotly: {plotly.__version__} | Streamlit: {st.__version__}")
    test_causa_enum_members()
    test_modificadores_sem_causas_orfas()
    test_validacao_detecta_causa_orfa()
    test_chuva_forte_modificador()
    test_detector_fallback_warnings()
    test_tipo_infracao_nao_mapeado_emite_error()
    print("\n====================================================")
    print(" TODOS OS TESTES PASSARAM COM SUCESSO! ")
    print("====================================================")
