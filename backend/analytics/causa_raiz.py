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

    # ── Modificadores de contexto (hipótese externa: clima, calendário, fluxo) ──
    # Cada modificador indica: (causa_afetada, incremento_absoluto)
    # Após aplicar, todas as probabilidades são renormalizadas para somar 1.0.

    MODIFICADORES_CONTEXTO: dict[str, list[tuple[str, float]]] = {
        "chuva_forte":   [(Causa.SINALIZACAO_POUCO_VISIVEL.value, 0.25)],
        "horario_pico":  [(Causa.CONGESTIONAMENTO.value,          0.20)],
        "obra_viaria":   [(Causa.SINALIZACAO_POUCO_VISIVEL.value, 0.15)],
        "dia_jogo":      [(Causa.CONGESTIONAMENTO.value,          0.15)],
        "feriado":       [(Causa.CONDUTA_DO_CONDUTOR.value,       0.10)],
    }

    # Alias retrocompatível: código existente que importa/usa MODIFICADORES
    # continua funcionando sem alteração.
    MODIFICADORES = MODIFICADORES_CONTEXTO

    # ── Modificadores de evidência (o que foi medido na cena) ───────────────────
    # Mesma estrutura de MODIFICADORES_CONTEXTO. Vazio por enquanto — será
    # populado em um passo futuro.
    MODIFICADORES_EVIDENCIA: dict[str, list[tuple[str, float]]] = {}

    # ── API pública ───────────────────────────────────────────────────────────

    def calcular_probabilidades(
        self,
        tipo_infracao: str,
        contexto: dict,
        evidencias: dict | None = None,
    ) -> dict:
        """Calcula as causas prováveis para uma infração dado o contexto e,
        opcionalmente, as evidências medidas na cena.

        Args:
            tipo_infracao: chave da infração (ex: "AVANCO_SINAL_VERMELHO").
            contexto:      dict retornado por GerenciadorContextoUrbano.obter_contexto_atual()
                           (hipótese externa: chuva, pico, obra, jogo, feriado).
            evidencias:    dict opcional no mesmo formato de flags que contexto,
                           mas representando o que foi medido na cena. Quando
                           None, nenhum modificador de evidência é aplicado.

        Returns:
            dict com:
              - "causa_principal":  str — nome da causa com maior probabilidade
              - "confianca":        float — probabilidade da causa principal (0-1)
              - "distribuicao":     dict[str, float] — todas as causas com suas %
                                     após modificadores de contexto e evidência
              - "fatores_ativos":   list[str] — nomes legíveis dos cenários ligados
              - "distribuicao_base": dict[str, float] — distribuição ANTES de
                                     qualquer modificador de contexto/evidência
              - "contribuicoes":    list[dict] — cada modificador efetivamente aplicado,
                                     contendo chaves "fonte", "causa" e "pontos"
              - "origem":           str — o que moveu a causa vencedora:
                                     "contexto", "evidencia", "ambos" ou "nenhuma"
        """
        contexto = contexto or {}
        base = self.TABELA_PROBABILIDADES_BASE.get(tipo_infracao)
        if base is None:
            logger.error(
                "Tipo de infração não mapeado em TABELA_PROBABILIDADES_BASE: %r. "
                "Verifique se o nome bate com o usado nas regras de detecção.",
                tipo_infracao,
            )
            return {
                "causa_principal":   "Desconhecida",
                "confianca":         0.0,
                "distribuicao":      {},
                "fatores_ativos":    contexto.get("fatores_ativos", []),
                "distribuicao_base": {},
                "contribuicoes":     [],
                "origem":            "nenhuma",
            }

        evidencias = evidencias or {}
        probs = copy.deepcopy(base)
        contribuicoes: list[dict] = []

        # Aplicar modificadores de contexto (hipótese externa)
        for chave_contexto, ajustes in self.MODIFICADORES_CONTEXTO.items():
            if contexto.get(chave_contexto, False):
                for causa, incremento in ajustes:
                    probs[causa] = probs.get(causa, 0.0) + incremento
                    contribuicoes.append({"fonte": "contexto", "causa": causa, "pontos": incremento})

        # Aplicar modificadores de evidência (o que foi medido na cena)
        for chave_evidencia, ajustes in self.MODIFICADORES_EVIDENCIA.items():
            if evidencias.get(chave_evidencia, False):
                for causa, incremento in ajustes:
                    probs[causa] = probs.get(causa, 0.0) + incremento
                    contribuicoes.append({"fonte": "evidencia", "causa": causa, "pontos": incremento})

        # Normalizar para somar 1.0
        probs = self._normalizar(probs)

        # Determinar a causa principal
        causa_top = max(probs.items(), key=lambda kv: (kv[1], kv[0]))[0]
        origem = self._determinar_origem(causa_top, contribuicoes)

        return {
            "causa_principal":   causa_top,
            "confianca":         round(probs[causa_top], 4),
            "distribuicao":      {k: round(v, 4) for k, v in probs.items()},
            "fatores_ativos":    contexto.get("fatores_ativos", []),
            "distribuicao_base": {k: round(v, 4) for k, v in base.items()},
            "contribuicoes":     contribuicoes,
            "origem":            origem,
        }

    def calcular_com_contrafactual(
        self,
        tipo_infracao: str,
        contexto: dict,
        evidencias: dict | None = None,
    ) -> dict:
        """Compara o resultado real com o que se obteria sem nenhum fator externo.

        Roda calcular_probabilidades duas vezes — uma com o contexto/evidências
        completos ("real") e outra com contexto e evidências vazios ("neutro") —
        para isolar o quanto os modificadores externos mudaram o diagnóstico.

        Args:
            tipo_infracao: chave da infração (ex: "AVANCO_SINAL_VERMELHO").
            contexto:      dict de contexto urbano completo.
            evidencias:    dict opcional de evidências da cena.

        Returns:
            dict com "real", "neutro" (ambos no formato de calcular_probabilidades)
            e "mudou_causa" (bool, True se a causa vencedora diverge entre os dois).
        """
        contexto = contexto or {}
        real = self.calcular_probabilidades(tipo_infracao, contexto, evidencias)
        neutro = self.calcular_probabilidades(tipo_infracao, {}, {})
        return {
            "real":        real,
            "neutro":      neutro,
            "mudou_causa": real["causa_principal"] != neutro["causa_principal"],
        }

    # ── Utilitários internos ──────────────────────────────────────────────────

    @staticmethod
    def _normalizar(probs: dict[str, float]) -> dict[str, float]:
        """Normaliza probabilidades para somar 1.0."""
        total = sum(probs.values())
        if total <= 0:
            return probs
        return {k: v / total for k, v in probs.items()}

    @staticmethod
    def _determinar_origem(
        causa_top: str,
        contribuicoes: list[dict],
    ) -> str:
        """Determina qual fonte (contexto, evidência, ambos ou nenhuma) moveu
        a causa vencedora, a partir do registro de contribuições aplicadas.
        """
        fontes = {c["fonte"] for c in contribuicoes if c["causa"] == causa_top}
        if fontes == {"contexto"}:
            return "contexto"
        if fontes == {"evidencia"}:
            return "evidencia"
        if fontes == {"contexto", "evidencia"}:
            return "ambos"
        return "nenhuma"

    # ── Representação ─────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        tipos = list(self.TABELA_PROBABILIDADES_BASE.keys())
        return f"<MotorCausaRaiz tipos={tipos}>"


def validar_tabela_base() -> None:
    """Valida se a soma das probabilidades base para cada tipo de infração é exatamente 1.0.

    Decisão de design:
    Esta validação é acionada primariamente dentro da suíte de testes automatizados
    (CI/CD e pytest) para não impactar o tempo de importação em produção, mantendo
    a integridade dos dados garantida antes de qualquer deploy.
    """
    for tipo, causas in MotorCausaRaiz.TABELA_PROBABILIDADES_BASE.items():
        soma = sum(causas.values())
        if abs(soma - 1.0) >= 1e-9:
            raise AssertionError(
                f"TABELA_PROBABILIDADES_BASE[{tipo!r}] soma {soma}, esperado 1.0"
            )


def _validar_consistencia_modificadores() -> None:
    """Garante que toda causa referenciada em MODIFICADORES_CONTEXTO ou
    MODIFICADORES_EVIDENCIA existe em pelo menos uma entrada de
    TABELA_PROBABILIDADES_BASE.
    """
    causas_base: set[str] = {
        causa
        for sub_tabela in MotorCausaRaiz.TABELA_PROBABILIDADES_BASE.values()
        for causa in sub_tabela.keys()
    }
    tabelas_modificadores = {
        "MODIFICADORES_CONTEXTO": MotorCausaRaiz.MODIFICADORES_CONTEXTO,
        "MODIFICADORES_EVIDENCIA": MotorCausaRaiz.MODIFICADORES_EVIDENCIA,
    }
    for nome_tabela, tabela in tabelas_modificadores.items():
        for cenario, ajustes in tabela.items():
            for causa, _ in ajustes:
                if causa not in causas_base:
                    raise AssertionError(
                        f"Causa órfã detectada no modificador '{cenario}' "
                        f"({nome_tabela}): '{causa}' não existe em nenhuma "
                        f"entrada de TABELA_PROBABILIDADES_BASE."
                    )


# Validação executada na inicialização do módulo
_validar_consistencia_modificadores()

