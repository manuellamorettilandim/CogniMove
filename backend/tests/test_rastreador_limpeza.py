"""
Testes Unitários — Limpeza de Tracks Inativos no Rastreador

Garante que o dicionário de tracks do Rastreador não cresça indefinidamente
ao longo de milhares de frames, expurgando veículos que saíram de cena.
"""
from __future__ import annotations

from unittest.mock import MagicMock
import numpy as np
import pytest

from backend.detection.infracoes.rastreador import Rastreador, VehicleTrack


def _criar_mock_box(track_id: int, cls_id: int = 2):
    box = MagicMock()
    box.id = [track_id]
    box.cls = [cls_id]
    box.conf = [0.90]
    box.xyxy = np.array([[100, 100, 200, 200]])
    return box


def test_rastreador_limpeza_periodica_tracks_inativos(monkeypatch):
    """
    (3) Simula mais de 1000 frames com múltiplos tracks entrando e saindo de cena.
    Valida que ao atingir o intervalo de limpeza (frame 1000), os tracks inativos
    há mais de 300 frames são expurgados do dicionário.
    """
    # Mock do YOLO para execução leve e determinística sem carregar pesos reais
    mock_model = MagicMock()
    mock_model.names = {2: "Carro"}
    monkeypatch.setattr("backend.detection.infracoes.rastreador.YOLO", lambda path: mock_model)

    rastreador = Rastreador("mock_model.pt", max_frames_inativo=300, intervalo_limpeza=1000)

    # Frame 1 a 100: Veículos 1 e 2 passam e saem de cena (last_seen = 100)
    mock_result_1_2 = MagicMock()
    mock_result_1_2.boxes = [_criar_mock_box(1), _criar_mock_box(2)]
    mock_model.track.return_value = [mock_result_1_2]

    dummy_frame = np.zeros((200, 200, 3), dtype=np.uint8)

    for _ in range(100):
        rastreador.update(dummy_frame)

    assert 1 in rastreador.tracks
    assert 2 in rastreador.tracks
    assert rastreador.tracks[1].last_seen == 100
    assert rastreador.tracks[2].last_seen == 100

    # Frame 101 a 999: Veículos 1 e 2 não são mais vistos; novos veículos temporários aparecem
    # Veículo 3 aparece no frame 800 a 850 (last_seen = 850, recente pois 850 >= 1000 - 300)
    # Veículo 4 ativo no frame 1000
    for f in range(101, 1000):
        if 800 <= f <= 850:
            mock_res = MagicMock()
            mock_res.boxes = [_criar_mock_box(3)]
            mock_model.track.return_value = [mock_res]
        else:
            mock_res = MagicMock()
            mock_res.boxes = []
            mock_model.track.return_value = [mock_res]

        rastreador.update(dummy_frame)

    # No frame 999 (antes da limpeza de 1000):
    assert 1 in rastreador.tracks
    assert 2 in rastreador.tracks
    assert 3 in rastreador.tracks

    # Frame 1000: Veículo 4 ativo (dispara a limpeza periódica frame_idx=1000)
    mock_result_1000 = MagicMock()
    mock_result_1000.boxes = [_criar_mock_box(4)]
    mock_model.track.return_value = [mock_result_1000]

    rastreador.update(dummy_frame)

    # Limite = 1000 - 300 = 700.
    # Veículos 1 e 2 (last_seen=100 < 700) devem ter sido expurgados.
    # Veículo 3 (last_seen=850 >= 700) deve ser mantido.
    # Veículo 4 (active=True) deve ser mantido.
    assert 1 not in rastreador.tracks, "Track 1 inativo há mais de 300 frames deveria ter sido removido."
    assert 2 not in rastreador.tracks, "Track 2 inativo há mais de 300 frames deveria ter sido removido."
    assert 3 in rastreador.tracks, "Track 3 inativo recentemente (< 300 frames) deve ser preservado."
    assert 4 in rastreador.tracks, "Track 4 ativo deve ser preservado."
    assert len(rastreador.tracks) == 2, f"Esperado 2 tracks remanescentes, mas encontrou {len(rastreador.tracks)}."
