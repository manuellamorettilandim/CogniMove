"""
CogniMove — Utilitários de Tratamento e Extração de Dados do Dashboard
"""
from __future__ import annotations

import logging
from contextlib import contextmanager

import pandas as pd


def obter_causa_predominante(
    df: pd.DataFrame,
    coluna: str = "causa_principal",
    default: str = "N/A",
) -> str:
    """Retorna o valor mais frequente da coluna, ou `default` se não houver valores válidos."""
    if coluna not in df.columns:
        return default
    moda = df[coluna].mode()
    return str(moda.iloc[0]) if not moda.empty else default


def resumir_contexto(contexto: dict | None) -> str:
    """Monta a frase legível com os fatores urbanos ativos de um contexto.

    Recebe o dict devolvido por `construir_contexto_a_partir_de_data` e
    devolve algo como:
        "🌧️ Chuva forte (4.2 mm/h) — 🕐 Horário de pico — 🎉 Feriado"
    """
    if not contexto:
        return "Contexto ainda não consultado."

    detalhes = contexto.get("_detalhes") or {}
    partes: list[str] = []

    if contexto.get("chuva_forte"):
        mm = detalhes.get("precipitacao_mm") or 0.0
        partes.append(f"🌧️ Chuva forte ({mm:.1f} mm/h)")
    if contexto.get("horario_pico"):
        partes.append("🕐 Horário de pico")
    if contexto.get("dia_jogo"):
        partes.append(f"⚽ {detalhes.get('confronto') or 'Jogo na cidade'}")
    if contexto.get("feriado"):
        partes.append("🎉 Feriado")
    if contexto.get("obra_viaria"):
        partes.append("🚧 Obra viária")

    return " — ".join(partes) if partes else "Nenhum fator de risco identificado."


class _ColetorDeAvisos(logging.Handler):
    """Handler que apenas acumula as mensagens de aviso emitidas por um logger."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.mensagens: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.mensagens.append(record.getMessage())


@contextmanager
def coletar_avisos(nome_logger: str):
    """Captura os warnings emitidos por um logger durante o bloco `with`.

    Uso:
        with coletar_avisos(minha_funcao.__module__) as avisos:
            minha_funcao()
        # `avisos` agora é a lista de mensagens capturadas
    """
    logger = logging.getLogger(nome_logger)
    coletor = _ColetorDeAvisos()
    nivel_anterior = logger.level
    logger.setLevel(logging.WARNING)
    logger.addHandler(coletor)
    try:
        yield coletor.mensagens
    finally:
        logger.removeHandler(coletor)
        logger.setLevel(nivel_anterior)


def traduzir_avisos_contexto(mensagens: list[str]) -> list[str]:
    """Converte os avisos técnicos das fontes externas em texto para o usuário.

    Remove duplicatas preservando a ordem de ocorrência.
    """
    amigaveis: list[str] = []
    for m in mensagens:
        texto = m.lower()
        if "clima" in texto or "open-meteo" in texto:
            amigaveis.append("Não foi possível confirmar o clima — assumindo sem chuva.")
        elif "jogo" in texto or "sportsdb" in texto:
            amigaveis.append("Não foi possível confirmar jogos na cidade — assumindo sem jogo.")
        else:
            amigaveis.append(f"Fonte externa indisponível: {m}")

    vistos: set[str] = set()
    unicos: list[str] = []
    for a in amigaveis:
        if a not in vistos:
            vistos.add(a)
            unicos.append(a)
    return unicos
