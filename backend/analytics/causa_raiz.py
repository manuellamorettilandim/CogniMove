"""
CogniMove — Motor de Análise de Causa-Raiz (Módulo 2)

Calcula probabilidades de causas infracionais com base no tipo de
infração detectada e no contexto urbano ativo naquele instante.

Baseado na Tabela 1 e Seção 4.2 do artigo:
  "Análise de Causa-Raiz — correlação probabilística entre infrações
   detectadas e variáveis urbanísticas."
"""
from __future__ import annotations

import copy
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class Causa(str, Enum):
    """Constantes para as causas-raiz catalogadas no sistema."""
    TEMPO_SEMAFORICO_INADEQUADO = "Tempo semafórico inadequado"
    CONGESTIONAMENTO = "Congestionamento"
    CONDUTA_DO_CONDUTOR = "Conduta do condutor"
    SINALIZACAO_POUCO_VISIVEL = "Sinalização pouco visível"
    PINTURA_DESGASTADA_AUSENTE = "Pintura desgastada / ausente"
    AUSENCIA_DE_SEGREGADOR_FISICO = "Ausência de segregador físico"


class MotorCausaRaiz:
    """Inferência probabilística simplificada para diagnóstico de infrações.

    Recebe o tipo de infração e o contexto urbano, aplica modificadores
    condicionais e retorna as causas prováveis ranqueadas.
    """

    # ── Tabela 1 do artigo — probabilidades base (soma = 1.0) ─────────────────

    TABELA_PROBABILIDADES_BASE: dict[str, dict[str, float]] = {
        "AVANCO_SINAL_VERMELHO": {
            Causa.TEMPO_SEMAFORICO_INADEQUADO.value: 0.35,
            Causa.CONGESTIONAMENTO.value:            0.25,
            Causa.CONDUTA_DO_CONDUTOR.value:         0.25,
            Causa.SINALIZACAO_POUCO_VISIVEL.value:   0.15,
        },
        "INVASAO_FAIXA": {
            Causa.PINTURA_DESGASTADA_AUSENTE.value:  0.35,
            Causa.SINALIZACAO_POUCO_VISIVEL.value:   0.25,
            Causa.AUSENCIA_DE_SEGREGADOR_FISICO.value: 0.20,
            Causa.CONDUTA_DO_CONDUTOR.value:         0.20,
        },
        "BLOQUEIO_CRUZAMENTO": {
            Causa.CONGESTIONAMENTO.value:            0.45,
            Causa.TEMPO_SEMAFORICO_INADEQUADO.value: 0.25,
            Causa.CONDUTA_DO_CONDUTOR.value:         0.20,
            Causa.SINALIZACAO_POUCO_VISIVEL.value:   0.10,
        },
    }

    # ── Modificadores contextuais ─────────────────────────────────────────────
    # Cada modificador indica: (causa_afetada, incremento_absoluto)
    # Após aplicar, todas as probabilidades são renormalizadas para somar 1.0.

    MODIFICADORES: dict[str, list[tuple[str, float]]] = {
        "chuva_forte":   [(Causa.SINALIZACAO_POUCO_VISIVEL.value, 0.25)],
        "horario_pico":  [(Causa.CONGESTIONAMENTO.value,          0.20)],
        "obra_viaria":   [(Causa.SINALIZACAO_POUCO_VISIVEL.value, 0.15)],
        "dia_jogo":      [(Causa.CONGESTIONAMENTO.value,          0.15)],
        "feriado":       [(Causa.CONDUTA_DO_CONDUTOR.value,       0.10)],
    }

    # ── API pública ───────────────────────────────────────────────────────────

    def calcular_probabilidades(
        self,
        tipo_infracao: str,
        contexto: dict,
    ) -> dict:
        """Calcula as causas prováveis para uma infração dada o contexto.

        Args:
            tipo_infracao: chave da infração (ex: "AVANCO_SINAL_VERMELHO").
            contexto:      dict retornado por GerenciadorContextoUrbano.obter_contexto_atual().

        Returns:
            dict com:
              - "causa_principal": str — nome da causa com maior probabilidade
              - "confianca":      float — probabilidade da causa principal (0-1)
              - "distribuicao":   dict[str, float] — todas as causas com suas %
              - "fatores_ativos": list[str] — nomes legíveis dos cenários ligados
        """
        base = self.TABELA_PROBABILIDADES_BASE.get(tipo_infracao)
        if base is None:
            logger.error(
                "Tipo de infração não mapeado em TABELA_PROBABILIDADES_BASE: %r. "
                "Verifique se o nome bate com o usado nas regras de detecção.",
                tipo_infracao,
            )
            return {
                "causa_principal": "Desconhecida",
                "confianca":       0.0,
                "distribuicao":    {},
                "fatores_ativos":  contexto.get("fatores_ativos", []),
            }

        probs = copy.deepcopy(base)

        # Aplicar modificadores dos cenários ativos
        for chave_contexto, ajustes in self.MODIFICADORES.items():
            if contexto.get(chave_contexto, False):
                for causa, incremento in ajustes:
                    probs[causa] = probs.get(causa, 0.0) + incremento

        # Normalizar para somar 1.0
        probs = self._normalizar(probs)

        # Determinar a causa principal
        causa_top = max(probs, key=probs.get)

        return {
            "causa_principal": causa_top,
            "confianca":       round(probs[causa_top], 4),
            "distribuicao":    {k: round(v, 4) for k, v in probs.items()},
            "fatores_ativos":  contexto.get("fatores_ativos", []),
        }

    # ── Utilitários internos ──────────────────────────────────────────────────

    @staticmethod
    def _normalizar(probs: dict[str, float]) -> dict[str, float]:
        """Normaliza probabilidades para somar 1.0."""
        total = sum(probs.values())
        if total <= 0:
            return probs
        return {k: v / total for k, v in probs.items()}

    # ── Representação ─────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        tipos = list(self.TABELA_PROBABILIDADES_BASE.keys())
        return f"<MotorCausaRaiz tipos={tipos}>"


def _validar_consistencia_modificadores() -> None:
    """Garante que toda causa referenciada em MODIFICADORES existe em pelo menos
    uma entrada de TABELA_PROBABILIDADES_BASE.
    """
    causas_base: set[str] = {
        causa
        for sub_tabela in MotorCausaRaiz.TABELA_PROBABILIDADES_BASE.values()
        for causa in sub_tabela.keys()
    }
    for cenario, ajustes in MotorCausaRaiz.MODIFICADORES.items():
        for causa, _ in ajustes:
            if causa not in causas_base:
                raise AssertionError(
                    f"Causa órfã detectada no modificador '{cenario}': '{causa}' "
                    f"não existe em nenhuma entrada de TABELA_PROBABILIDADES_BASE."
                )


# Validação executada na inicialização do módulo
_validar_consistencia_modificadores()
