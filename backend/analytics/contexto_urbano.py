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

    # Mapeamento de nomes legíveis para relatórios e UI
    NOMES_FATORES: dict[str, str] = {
        "chuva_forte":  "Chuva Forte / Baixa Visibilidade",
        "dia_jogo":     "Dia de Jogo / Evento de Grande Porte",
        "horario_pico": "Horário de Pico",
        "feriado":      "Feriado",
        "obra_viaria":  "Obra Viária / Desvio",
    }

    # ── Construtor ────────────────────────────────────────────────────────────

    def __init__(self):
        self._lock = threading.Lock()

        # Cenários simuláveis armazenados em dicionário unificado
        self._flags: dict[str, bool] = {
            "chuva_forte": False,
            "dia_jogo": False,
            "horario_pico": False,
            "feriado": False,
            "obra_viaria": False,
        }

    # ── Getters de estado ─────────────────────────────────────────────────────

    def obter_contexto_atual(self) -> dict:
        """Retorna um snapshot imutável de todos os cenários ativos.

        Returns:
            dict com chaves booleanas para cada fator e uma lista resumo
            dos nomes dos fatores que estão ligados.
        """
        with self._lock:
            ctx = {
                **self._flags,
                "timestamp": datetime.datetime.now().isoformat(),
            }

        ctx["fatores_ativos"] = [
            self.NOMES_FATORES[k] for k in self.NOMES_FATORES if ctx.get(k)
        ]
        return ctx

    # ── Setter genérico ───────────────────────────────────────────────────────

    def set_flag(self, nome: str, estado: bool) -> None:
        """Define o estado de um cenário urbano por chave.

        Args:
            nome: Nome da flag (ex: 'chuva_forte', 'horario_pico').
            estado: Booleano indicando se o cenário está ativo.

        Raises:
            KeyError: Se o nome do cenário não existir em self._flags.
        """
        if nome not in self._flags:
            raise KeyError(f"Cenário urbano desconhecido: {nome!r}")
        with self._lock:
            self._flags[nome] = bool(estado)

    # ── Setters individuais (delegam para set_flag) ───────────────────────────

    def set_chuva_forte(self, estado: bool) -> None:
        self.set_flag("chuva_forte", estado)

    def set_dia_jogo(self, estado: bool) -> None:
        self.set_flag("dia_jogo", estado)

    def set_horario_pico(self, estado: bool) -> None:
        self.set_flag("horario_pico", estado)

    def set_feriado(self, estado: bool) -> None:
        self.set_flag("feriado", estado)

    def set_obra_viaria(self, estado: bool) -> None:
        self.set_flag("obra_viaria", estado)

    # ── Setter em lote (usado pelo Streamlit) ─────────────────────────────────

    def atualizar_contexto(
        self,
        chuva_forte: bool = False,
        dia_jogo: bool = False,
        horario_pico: bool = False,
        feriado: bool = False,
        obra_viaria: bool = False,
    ) -> None:
        """Atualiza todos os cenários de uma vez de forma atômica."""
        with self._lock:
            self._flags["chuva_forte"]  = bool(chuva_forte)
            self._flags["dia_jogo"]     = bool(dia_jogo)
            self._flags["horario_pico"] = bool(horario_pico)
            self._flags["feriado"]      = bool(feriado)
            self._flags["obra_viaria"]  = bool(obra_viaria)

    # ── Representação ─────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        ctx = self.obter_contexto_atual()
        ativos = ctx["fatores_ativos"] or ["Nenhum"]
        return f"<ContextoUrbano ativos={ativos}>"
