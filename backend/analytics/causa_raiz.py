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


class MotorCausaRaiz:
    """Inferência probabilística simplificada para diagnóstico de infrações.

    Recebe o tipo de infração e o contexto urbano, aplica modificadores
    condicionais e retorna as causas prováveis ranqueadas.
    """

    # ── Tabela 1 do artigo — probabilidades base (soma = 1.0) ─────────────────

    TABELA_PROBABILIDADES_BASE: dict[str, dict[str, float]] = {
        "AVANCO_SINAL_VERMELHO": {
            "Tempo semafórico inadequado":     0.35,
            "Congestionamento":                0.25,
            "Conduta do condutor":             0.25,
            "Sinalização pouco visível":       0.15,
        },
        "INVASAO_FAIXA": {
            "Pintura desgastada / ausente":    0.35,
            "Sinalização pouco visível":       0.25,
            "Ausência de segregador físico":   0.20,
            "Conduta do condutor":             0.20,
        },
        "BLOQUEIO_CRUZAMENTO": {
            "Congestionamento":                0.45,
            "Tempo semafórico inadequado":     0.25,
            "Conduta do condutor":             0.20,
            "Sinalização pouco visível":       0.10,
        },
    }

    # ── Modificadores contextuais ─────────────────────────────────────────────
    # Cada modificador indica: (causa_afetada, incremento_absoluto)
    # Após aplicar, todas as probabilidades são renormalizadas para somar 1.0.

    MODIFICADORES: dict[str, tuple[str, float]] = {
        "chuva_forte":   ("Baixa visibilidade",           0.25),
        "horario_pico":  ("Congestionamento",              0.20),
        "obra_viaria":   ("Sinalização pouco visível",     0.15),
        "dia_jogo":      ("Congestionamento",              0.15),
        "feriado":       ("Conduta do condutor",            0.10),
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
            return {
                "causa_principal": "Desconhecida",
                "confianca":       0.0,
                "distribuicao":    {},
                "fatores_ativos":  contexto.get("fatores_ativos", []),
            }

        probs = copy.deepcopy(base)

        # Aplicar modificadores dos cenários ativos
        for chave_contexto, (causa, incremento) in self.MODIFICADORES.items():
            if contexto.get(chave_contexto, False):
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
