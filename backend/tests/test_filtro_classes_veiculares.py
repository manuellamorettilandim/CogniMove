"""
Testes Unitários — Filtragem de Classes Veiculares para Regras de Infração

Garante que pedestres (COCO class 0) continuem sendo rastreados/exibidos,
mas nunca gerem autuações em RegraFaixaPedestre, RegraBloqueioCruzamento ou RegraSinalVermelho.
"""
from __future__ import annotations

import pytest
from backend.detection.infracoes.rastreador import (
    VehicleTrack,
    VEHICLE_CLASSES,
    CLASSES_VEICULARES,
)
from backend.detection.infracoes.regras.faixa_pedestre import RegraFaixaPedestre
from backend.detection.infracoes.regras.bloqueio_cruzamento import RegraBloqueioCruzamento


def test_constantes_classes():
    """Valida a separação entre VEHICLE_CLASSES (geral) e CLASSES_VEICULARES (infratores)."""
    assert 0 in VEHICLE_CLASSES, "Pedestre (classe 0) deve permanecer em VEHICLE_CLASSES para rastreamento visual."
    assert 0 not in CLASSES_VEICULARES, "Pedestre (classe 0) NÃO deve estar em CLASSES_VEICULARES."
    for cls_id in [1, 2, 3, 5, 7]:
        assert cls_id in CLASSES_VEICULARES, f"Classe de veículo {cls_id} deve estar em CLASSES_VEICULARES."


def test_pedestre_na_faixa_nao_gera_infracao_apos_filtro():
    """
    Simula um pedestre (cls_id=0) posicionado dentro do polígono de faixa de pedestres.
    Valida que, após a filtragem por CLASSES_VEICULARES, nenhuma infração é gerada.
    """
    poly_zone = {
        "name": "Faixa de Pedestres Centro",
        "points": [[100, 100], [300, 100], [300, 300], [100, 300]],
    }
    regra_faixa = RegraFaixaPedestre(lines=[], polygons=[poly_zone], cooldown_frames=5)

    # 1. Pedestre atravessando / parado na faixa (classe 0)
    track_pedestre = VehicleTrack(track_id=1, cls_id=0, cls_name="Pedestre")
    track_pedestre.update(frame_idx=1, bbox=(150, 150, 200, 250), conf=0.90)  # Dentro do polígono

    tracks_ativos = [track_pedestre]

    # Aplicação do filtro conforme detector._process_frame
    tracks_veiculares = [t for t in tracks_ativos if t.cls_id in CLASSES_VEICULARES]
    assert len(tracks_veiculares) == 0, "O track de pedestre deve ser filtrado da lista veicular."

    infracoes = regra_faixa.checar(None, tracks_veiculares, "unknown", frame_idx=1)
    assert len(infracoes) == 0, "Pedestre na faixa NÃO deve gerar infração INVASAO_FAIXA."


def test_veiculo_na_faixa_gera_infracao_apos_filtro():
    """
    Garante que um carro (cls_id=2) na mesma posição é mantido pelo filtro e gera infração.
    """
    poly_zone = {
        "name": "Faixa de Pedestres Centro",
        "points": [[100, 100], [300, 100], [300, 300], [100, 300]],
    }
    regra_faixa = RegraFaixaPedestre(lines=[], polygons=[poly_zone], cooldown_frames=5)

    # 2. Carro invadindo a faixa (classe 2)
    track_carro = VehicleTrack(track_id=2, cls_id=2, cls_name="Carro")
    track_carro.update(frame_idx=1, bbox=(150, 150, 200, 250), conf=0.90)

    tracks_ativos = [track_carro]
    tracks_veiculares = [t for t in tracks_ativos if t.cls_id in CLASSES_VEICULARES]
    assert len(tracks_veiculares) == 1, "O track de carro deve ser preservado pelo filtro veicular."

    infracoes = regra_faixa.checar(None, tracks_veiculares, "unknown", frame_idx=1)
    assert len(infracoes) == 1, "Carro sobre a faixa deve gerar infração INVASAO_FAIXA."
    assert infracoes[0]["tipo"] == "INVASAO_FAIXA"
    assert infracoes[0]["track_id"] == 2


def test_pedestre_no_cruzamento_nao_gera_bloqueio_apos_filtro():
    """
    Garante que uma pessoa parada no cruzamento não é autuada por BLOQUEIO_CRUZAMENTO.
    """
    zona_cruzamento = {
        "name": "Cruzamento Central",
        "points": [[100, 100], [400, 100], [400, 400], [100, 400]],
    }
    regra_bloq = RegraBloqueioCruzamento([zona_cruzamento], fps=10.0, threshold_seconds=1.0)

    track_pedestre = VehicleTrack(track_id=3, cls_id=0, cls_name="Pedestre")
    for f in range(1, 20):
        track_pedestre.update(frame_idx=f, bbox=(200, 200, 250, 300), conf=0.95)

    # Filtro aplicado a cada frame
    tracks_veiculares = [t for t in [track_pedestre] if t.cls_id in CLASSES_VEICULARES]
    assert len(tracks_veiculares) == 0

    infracoes_f1 = regra_bloq.checar(None, tracks_veiculares, "unknown", frame_idx=1)
    infracoes_f15 = regra_bloq.checar(None, tracks_veiculares, "unknown", frame_idx=15)

    assert len(infracoes_f1) == 0
    assert len(infracoes_f15) == 0
