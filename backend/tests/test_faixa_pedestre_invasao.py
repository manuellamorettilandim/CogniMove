"""
Testes Unitários — Invasão de Polígono como Evento de Entrada

RegraFaixaPedestre._check_polygon_invasion testava um ESTADO ("o ponto está
dentro do polígono?"), então um veículo parado dentro da área voltava a
disparar infração a cada cooldown_frames. Estes testes garantem que a
invasão agora é tratada como EVENTO (transição de fora para dentro), sem
carregar vídeo nem modelo YOLO — apenas tracks falsos com posições
controladas manualmente.
"""
from __future__ import annotations

import pytest

from backend.detection.infracoes.regras.faixa_pedestre import RegraFaixaPedestre

POLIGONO = {
    "name": "Faixa Protegida",
    "points": [(100, 100), (200, 100), (200, 200), (100, 200)],
}
PONTO_DENTRO   = (150, 150)
PONTO_FORA     = (50, 50)


class FakeTrack:
    """Track falso: só o suficiente para exercitar RegraFaixaPedestre."""

    def __init__(self, track_id: int, cls_name: str = "Carro"):
        self.id = track_id
        self.cls_name = cls_name
        self.active = True
        self.history: list[dict] = []

    def mover_para(self, bottom_pt: tuple[int, int]):
        x, y = bottom_pt
        self.history.append({
            "bbox": (x - 10, y - 20, x + 10, y),
            "bottom_pt": bottom_pt,
            "conf": 0.90,
        })

    @property
    def current(self) -> dict | None:
        return self.history[-1] if self.history else None

    @property
    def previous(self) -> dict | None:
        return self.history[-2] if len(self.history) >= 2 else None


def _infracoes_de_invasao(infracoes: list[dict]) -> list[dict]:
    return [i for i in infracoes if i["descricao"].startswith("Invasão de")]


def test_track_permanece_dentro_gera_exatamente_uma_infracao():
    """(a) Track entra no polígono e fica dentro por vários frames: 1 infração só."""
    regra = RegraFaixaPedestre(lines=[], polygons=[POLIGONO])
    track = FakeTrack(1)

    total_invasoes = 0
    frame_idx = 0

    # Fora do polígono
    track.mover_para(PONTO_FORA)
    frame_idx += 1
    total_invasoes += len(_infracoes_de_invasao(regra.checar(None, [track], "unknown", frame_idx)))

    # Entra e permanece dentro por 10 frames
    for _ in range(10):
        track.mover_para(PONTO_DENTRO)
        frame_idx += 1
        total_invasoes += len(_infracoes_de_invasao(regra.checar(None, [track], "unknown", frame_idx)))

    assert total_invasoes == 1


def test_track_sai_e_entra_de_novo_gera_duas_infracoes():
    """(b) Track sai do polígono e entra de novo: 2 infrações."""
    regra = RegraFaixaPedestre(lines=[], polygons=[POLIGONO])
    track = FakeTrack(1)

    total_invasoes = 0
    frame_idx = 0

    for _ in range(3):
        track.mover_para(PONTO_FORA)
        frame_idx += 1
        total_invasoes += len(_infracoes_de_invasao(regra.checar(None, [track], "unknown", frame_idx)))

    # 1ª entrada
    for _ in range(3):
        track.mover_para(PONTO_DENTRO)
        frame_idx += 1
        total_invasoes += len(_infracoes_de_invasao(regra.checar(None, [track], "unknown", frame_idx)))

    # Sai de novo
    for _ in range(3):
        track.mover_para(PONTO_FORA)
        frame_idx += 1
        total_invasoes += len(_infracoes_de_invasao(regra.checar(None, [track], "unknown", frame_idx)))

    # 2ª entrada
    for _ in range(3):
        track.mover_para(PONTO_DENTRO)
        frame_idx += 1
        total_invasoes += len(_infracoes_de_invasao(regra.checar(None, [track], "unknown", frame_idx)))

    assert total_invasoes == 2


def test_dois_tracks_dentro_geram_uma_infracao_cada():
    """(c) Dois tracks diferentes entram no polígono: 1 infração para cada um."""
    regra = RegraFaixaPedestre(lines=[], polygons=[POLIGONO])
    track1 = FakeTrack(1)
    track2 = FakeTrack(2)

    frame_idx = 1
    track1.mover_para(PONTO_FORA)
    track2.mover_para(PONTO_FORA)
    regra.checar(None, [track1, track2], "unknown", frame_idx)

    frame_idx += 1
    track1.mover_para(PONTO_DENTRO)
    track2.mover_para(PONTO_DENTRO)
    infracoes = _infracoes_de_invasao(regra.checar(None, [track1, track2], "unknown", frame_idx))

    assert len(infracoes) == 2
    assert {i["track_id"] for i in infracoes} == {1, 2}

    # Permanecendo dentro nos frames seguintes, não deve haver novas infrações
    frame_idx += 1
    track1.mover_para(PONTO_DENTRO)
    track2.mover_para(PONTO_DENTRO)
    infracoes_seguintes = _infracoes_de_invasao(regra.checar(None, [track1, track2], "unknown", frame_idx))
    assert infracoes_seguintes == []


def test_dentro_de_e_cooldown_sao_limpos_para_tracks_inativos():
    """(3) Tracks que somem da lista de ativos não devem crescer os dicionários internos."""
    regra = RegraFaixaPedestre(lines=[], polygons=[POLIGONO])
    track = FakeTrack(1)

    track.mover_para(PONTO_DENTRO)
    regra.checar(None, [track], "unknown", 1)
    assert 1 in regra._dentro_de

    # Track desaparece da lista (não está mais ativo)
    regra.checar(None, [], "unknown", 2)

    assert 1 not in regra._dentro_de
    assert 1 not in regra._cooldown
