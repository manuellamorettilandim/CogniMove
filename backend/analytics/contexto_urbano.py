"""
CogniMove — Módulo de Contexto Urbano (Módulo 3)

Gerencia o estado simulado do ambiente urbano em tempo real.
Permite que o dashboard (Streamlit) ative/desative cenários como
chuva, horário de pico, obras etc., e que o pipeline de detecção
consulte o contexto ativo para enriquecer cada infração registrada.

Baseado na Seção 4.3 do artigo:
  "Integração de Dados Urbanos — clima, eventos, fluxo de tráfego e obras."
"""
from __future__ import annotations

import threading
import datetime


class GerenciadorContextoUrbano:
    """Armazena e fornece o estado atual dos fatores urbanos simulados.

    Thread-safe: tanto o Streamlit quanto o loop de detecção podem
    acessar/modificar simultaneamente.
    """

    # ── Construtor ────────────────────────────────────────────────────────────

    def __init__(self):
        self._lock = threading.Lock()

        # Cenários simuláveis (todos inativos por padrão)
        self._chuva_forte: bool = False
        self._dia_jogo: bool = False
        self._horario_pico: bool = False
        self._feriado: bool = False
        self._obra_viaria: bool = False

    # ── Getters de estado ─────────────────────────────────────────────────────

    def obter_contexto_atual(self) -> dict:
        """Retorna um snapshot imutável de todos os cenários ativos.

        Returns:
            dict com chaves booleanas para cada fator e uma lista resumo
            dos nomes dos fatores que estão ligados.
        """
        with self._lock:
            ctx = {
                "chuva_forte":   self._chuva_forte,
                "dia_jogo":      self._dia_jogo,
                "horario_pico":  self._horario_pico,
                "feriado":       self._feriado,
                "obra_viaria":   self._obra_viaria,
                "timestamp":     datetime.datetime.now().isoformat(),
            }

        # Lista legível dos fatores ativos (útil para relatórios)
        _nomes = {
            "chuva_forte":  "Chuva Forte / Baixa Visibilidade",
            "dia_jogo":     "Dia de Jogo / Evento de Grande Porte",
            "horario_pico": "Horário de Pico",
            "feriado":      "Feriado",
            "obra_viaria":  "Obra Viária / Desvio",
        }
        ctx["fatores_ativos"] = [
            _nomes[k] for k in _nomes if ctx.get(k)
        ]
        return ctx

    # ── Setters individuais ───────────────────────────────────────────────────

    def set_chuva_forte(self, estado: bool) -> None:
        with self._lock:
            self._chuva_forte = estado

    def set_dia_jogo(self, estado: bool) -> None:
        with self._lock:
            self._dia_jogo = estado

    def set_horario_pico(self, estado: bool) -> None:
        with self._lock:
            self._horario_pico = estado

    def set_feriado(self, estado: bool) -> None:
        with self._lock:
            self._feriado = estado

    def set_obra_viaria(self, estado: bool) -> None:
        with self._lock:
            self._obra_viaria = estado

    # ── Setter em lote (usado pelo Streamlit) ─────────────────────────────────

    def atualizar_contexto(
        self,
        chuva_forte: bool = False,
        dia_jogo: bool = False,
        horario_pico: bool = False,
        feriado: bool = False,
        obra_viaria: bool = False,
    ) -> None:
        """Atualiza todos os cenários de uma vez."""
        with self._lock:
            self._chuva_forte  = chuva_forte
            self._dia_jogo     = dia_jogo
            self._horario_pico = horario_pico
            self._feriado      = feriado
            self._obra_viaria  = obra_viaria

    # ── Representação ─────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        ctx = self.obter_contexto_atual()
        ativos = ctx["fatores_ativos"] or ["Nenhum"]
        return f"<ContextoUrbano ativos={ativos}>"
