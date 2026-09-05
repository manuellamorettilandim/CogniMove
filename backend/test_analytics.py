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


if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print(f"Pandas: {pd.__version__} | Plotly: {plotly.__version__} | Streamlit: {st.__version__}")
    test_causa_enum_members()
    test_modificadores_sem_causas_orfas()
    test_validacao_detecta_causa_orfa()
    test_chuva_forte_modificador()
    print("\n====================================================")
    print(" TODOS OS TESTES PASSARAM COM SUCESSO! ")
    print("====================================================")
