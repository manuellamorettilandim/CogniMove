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


def formatar_selo_procedencia(dados_procedencia: dict | None) -> str:
    """Gera rótulo visual com ícone de procedência técnica (🟢, 🟡, ⚪).

    Níveis:
      - 🟢 Fonte primária (ex: "NT 195/96 CET-SP")
      - 🟡 Fonte secundária (ex: "Instituto de Engenharia")
      - ⚪ Estimativa da equipe

    Fallback seguro: qualquer entrada ausente ou inválida retorna ⚪ Estimativa da equipe.
    """
    if not isinstance(dados_procedencia, dict):
        return "⚪ Estimativa da equipe"

    nivel = dados_procedencia.get("nivel")
    fontes = dados_procedencia.get("fontes", [])

    nomes_fontes: list[str] = []
    if isinstance(fontes, list):
        for f in fontes:
            if isinstance(f, dict):
                cod = f.get("codigo")
                org = f.get("orgao")
                tit = f.get("titulo")
                if cod and org:
                    nomes_fontes.append(f"{cod} {org}")
                elif org:
                    nomes_fontes.append(str(org))
                elif cod:
                    nomes_fontes.append(str(cod))
                elif tit:
                    nomes_fontes.append(str(tit))

    sufixo = f" ({', '.join(nomes_fontes)})" if nomes_fontes else ""

    if nivel == "fonte_primaria":
        return f"🟢 Fonte primária{sufixo}"
    if nivel == "fonte_secundaria":
        return f"🟡 Fonte secundária{sufixo}"
    return "⚪ Estimativa da equipe"


def formatar_contrafactual_diagnostico(
    resultado_contrafactual: dict,
    limiar_diferenca_pct: float = 5.0,
) -> dict:
    """Formata as linhas de diagnóstico real e contrafactual para exibição na UI.

    Args:
        resultado_contrafactual: dict retornado por MotorCausaRaiz.calcular_com_contrafactual().
        limiar_diferenca_pct: diferença mínima em pontos percentuais para exibir contrafactual.

    Returns:
        dict com 'linha_real', 'linha_neutra', 'mostrar_neutra', 'causa_real', 'pct_real', etc.
    """
    real = resultado_contrafactual.get("real", {}) if isinstance(resultado_contrafactual, dict) else {}
    neutro = resultado_contrafactual.get("neutro", {}) if isinstance(resultado_contrafactual, dict) else {}
    mudou_causa = bool(resultado_contrafactual.get("mudou_causa", False)) if isinstance(resultado_contrafactual, dict) else False

    causa_real = str(real.get("causa_principal") or "Desconhecida")
    conf_real = float(real.get("confianca", 0.0) or 0.0)
    pct_real = round(conf_real * 100)

    fatores_ativos = real.get("fatores_ativos", []) or []
    fatores_str = ", ".join(fatores_ativos) if fatores_ativos else "nenhum fator ativo"

    linha_real = f"Com [{fatores_str}]: {causa_real} — {pct_real}%"

    causa_neutra = str(neutro.get("causa_principal") or "Desconhecida")
    conf_neutra = float(neutro.get("confianca", 0.0) or 0.0)
    pct_neutra = round(conf_neutra * 100)

    diff_pct = abs(pct_real - pct_neutra)
    mostrar_neutra = mudou_causa or (diff_pct >= limiar_diferenca_pct)

    linha_neutra = (
        f"Sem nenhum fator ativo seria: {causa_neutra} — {pct_neutra}%"
        if mostrar_neutra
        else None
    )

    return {
        "linha_real": linha_real,
        "linha_neutra": linha_neutra,
        "mostrar_neutra": mostrar_neutra,
        "causa_real": causa_real,
        "pct_real": pct_real,
        "causa_neutra": causa_neutra,
        "pct_neutra": pct_neutra,
        "mudou_causa": mudou_causa,
        "fatores_str": fatores_str,
    }


def extrair_procedencia_segura(chave_ou_causa: str, tipo: str = "causa") -> dict:
    """Consulta procedencia_causa ou procedencia_modificador com tratamento seguro de exceção."""
    try:
        from backend.analytics.fundamentacao import procedencia_causa, procedencia_modificador
    except Exception:
        try:
            from analytics.fundamentacao import procedencia_causa, procedencia_modificador
        except Exception:
            return {
                "nivel": "estimativa_equipe",
                "fontes": [],
                "justificativa": "Módulo de fundamentação indisponível.",
            }

    try:
        if tipo == "modificador":
            return procedencia_modificador(chave_ou_causa)
        return procedencia_causa(chave_ou_causa)
    except Exception:
        return {
            "nivel": "estimativa_equipe",
            "fontes": [],
            "justificativa": "Procedência não encontrada.",
        }


def montar_tabela_procedencia_causas(resultado_causa: dict) -> list[dict]:
    """Monta a lista de dicionários para exibição tabular das causas e selos de procedência."""
    distribuicao = resultado_causa.get("distribuicao", {}) if isinstance(resultado_causa, dict) else {}
    distribuicao_base = resultado_causa.get("distribuicao_base", {}) if isinstance(resultado_causa, dict) else {}

    linhas = []
    # Ordenar pela maior probabilidade final
    causas_ordenadas = sorted(
        distribuicao.keys(),
        key=lambda c: (distribuicao.get(c, 0.0), c),
        reverse=True,
    )

    for causa in causas_ordenadas:
        prob_final = float(distribuicao.get(causa, 0.0))
        prob_base = float(distribuicao_base.get(causa, 0.0))
        proc = extrair_procedencia_segura(causa, tipo="causa")
        selo = formatar_selo_procedencia(proc)

        linhas.append({
            "Causa-Raiz": causa,
            "Probabilidade Final": f"{prob_final * 100:.1f}%",
            "Probabilidade Base": f"{prob_base * 100:.1f}%",
            "Procedência Técnica": selo,
            "Justificativa": proc.get("justificativa", ""),
        })
    return linhas


def montar_resumo_contribuicoes(resultado_causa: dict, contexto: dict | None = None) -> dict:
    """Estrutura as contribuições aplicadas separando contexto de evidência e anexando selos."""
    contribuicoes = resultado_causa.get("contribuicoes", []) if isinstance(resultado_causa, dict) else []
    itens_contexto = []
    itens_evidencia = []

    for item in contribuicoes:
        if isinstance(item, (list, tuple)) and len(item) >= 3:
            fonte, causa, pts = item[0], item[1], item[2]
            proc_causa = extrair_procedencia_segura(str(causa), tipo="causa")
            selo_causa = formatar_selo_procedencia(proc_causa)
            pontos_val = float(pts)
            pts_str = f"+{pontos_val * 100:.0f} pts" if pontos_val >= 0 else f"{pontos_val * 100:.0f} pts"

            d = {
                "fonte": str(fonte),
                "causa": str(causa),
                "pontos": pontos_val,
                "pontos_formatado": pts_str,
                "selo_causa": selo_causa,
            }
            if fonte == "contexto":
                itens_contexto.append(d)
            elif fonte == "evidencia":
                itens_evidencia.append(d)

    # Modificadores de contexto ativos com seus selos de modificador
    modificadores_ativos = []
    if isinstance(contexto, dict):
        nomes_fatores = {
            "chuva_forte": "Chuva Forte / Baixa Visibilidade",
            "horario_pico": "Horário de Pico",
            "dia_jogo": "Dia de Jogo / Evento de Grande Porte",
            "feriado": "Feriado",
            "obra_viaria": "Obra Viária / Desvio",
        }
        for chave, nome_legivel in nomes_fatores.items():
            if contexto.get(chave):
                proc_mod = extrair_procedencia_segura(chave, tipo="modificador")
                selo_mod = formatar_selo_procedencia(proc_mod)
                modificadores_ativos.append({
                    "chave": chave,
                    "nome": nome_legivel,
                    "selo": selo_mod,
                    "justificativa": proc_mod.get("justificativa", ""),
                })

    return {
        "contexto": itens_contexto,
        "evidencia": itens_evidencia,
        "modificadores_ativos": modificadores_ativos,
        "total_contribuicoes": len(contribuicoes),
    }

