"""
CogniMove — Contexto Urbano em Tempo Real (Simulador de Câmera)

Consulta fontes de dados reais (feriados, clima, jogos de futebol) para
montar o contexto urbano de uma data/hora escolhida pelo usuário, no
formato que `GerenciadorContextoUrbano` / `MotorCausaRaiz` já esperam.

Nenhuma das integrações derruba a aplicação em caso de falha: toda
chamada de rede é protegida por try/except e, em caso de erro, loga um
aviso e assume o valor padrão (fail-safe), permitindo que a simulação
continue funcionando mesmo com uma fonte externa fora do ar.
"""
from __future__ import annotations

import datetime
import logging

import holidays
import requests

logger = logging.getLogger(__name__)

TIMEOUT_PADRAO = 5


def verificar_feriado(data: datetime.date, estado: str = "SP") -> bool:
    """Retorna True se a data for feriado nacional ou estadual (SP)."""
    br_feriados = holidays.Brazil(subdiv=estado)
    return data in br_feriados


def verificar_chuva_forte(
    data: datetime.date,
    hora: datetime.time,
    lat: float = -23.55,
    lon: float = -46.63,
    limiar_mm: float = 2.5,
) -> tuple[bool, float]:
    """Consulta precipitação histórica/prevista via Open-Meteo.

    Usa o endpoint de arquivo histórico para datas passadas/hoje e o
    endpoint de previsão para datas futuras. Retorna (chuva_forte, mm).
    """
    hoje = datetime.date.today()
    if data > hoje:
        url = "https://api.open-meteo.com/v1/forecast"
    else:
        url = "https://archive-api.open-meteo.com/v1/archive"

    try:
        resp = requests.get(
            url,
            params={
                "latitude": lat, "longitude": lon,
                "start_date": data.isoformat(), "end_date": data.isoformat(),
                "hourly": "precipitation", "timezone": "America/Sao_Paulo",
            },
            timeout=TIMEOUT_PADRAO,
        )
        resp.raise_for_status()
        dados = resp.json()
        horas = dados["hourly"]["time"]
        precipitacoes = dados["hourly"]["precipitation"]
        hora_alvo = f"{data.isoformat()}T{hora.strftime('%H:00')}"
        if hora_alvo in horas:
            idx = horas.index(hora_alvo)
            mm = precipitacoes[idx]
            return mm >= limiar_mm, mm
        return False, 0.0
    except Exception as e:
        logger.warning("Falha ao consultar clima (Open-Meteo): %s", e)
        return False, 0.0


def verificar_dia_de_jogo(
    data: datetime.date,
    times: tuple[str, ...] = ("Corinthians", "Palmeiras", "Sao Paulo", "Santos"),
) -> tuple[bool, str | None]:
    """Consulta jogos de futebol na data via TheSportsDB (chave de teste "3")."""
    try:
        resp = requests.get(
            "https://www.thesportsdb.com/api/v1/json/3/eventsday.php",
            params={"d": data.isoformat(), "s": "Soccer"},
            timeout=TIMEOUT_PADRAO,
        )
        resp.raise_for_status()
        eventos = resp.json().get("events") or []
        for ev in eventos:
            home, away = ev.get("strHomeTeam", ""), ev.get("strAwayTeam", "")
            for nome_time in times:
                if nome_time.lower() in home.lower() or nome_time.lower() in away.lower():
                    return True, f"{home} x {away}"
        return False, None
    except Exception as e:
        logger.warning("Falha ao consultar jogos (TheSportsDB): %s", e)
        return False, None


def verificar_horario_pico(hora: datetime.time, dia_semana: int) -> bool:
    """dia_semana: 0=segunda ... 6=domingo (use data.weekday())."""
    if dia_semana >= 5:
        return False
    manha = datetime.time(7, 0) <= hora <= datetime.time(9, 0)
    tarde = datetime.time(17, 0) <= hora <= datetime.time(19, 0)
    return manha or tarde


def construir_contexto_a_partir_de_data(
    data: datetime.date,
    hora: datetime.time,
    obra_viaria_manual: bool = False,
) -> dict:
    """Monta o contexto urbano completo para a data/hora escolhida.

    Consulta as 3 fontes reais, combina com o fator manual de obra
    viária e delega a montagem final para `GerenciadorContextoUrbano`,
    garantindo o mesmo formato de dict já consumido por `MotorCausaRaiz`.
    """
    from backend.analytics.contexto_urbano import GerenciadorContextoUrbano

    feriado = verificar_feriado(data)
    pico = verificar_horario_pico(hora, data.weekday())
    chuva, mm_chuva = verificar_chuva_forte(data, hora)
    jogo, confronto = verificar_dia_de_jogo(data)

    gerenciador = GerenciadorContextoUrbano()
    gerenciador.atualizar_contexto(
        chuva_forte=chuva,
        dia_jogo=jogo,
        horario_pico=pico,
        feriado=feriado,
        obra_viaria=obra_viaria_manual,
    )
    contexto = gerenciador.obter_contexto_atual()
    contexto["_detalhes"] = {
        "precipitacao_mm": mm_chuva,
        "confronto": confronto,
    }
    return contexto
