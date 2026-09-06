"""
Testes Unitários — Script de Avaliação do Modelo (avaliar_modelo.py)

Valida as funções de busca de vídeo, computação de estatísticas por frame e exportação para CSV.
"""
import csv
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from backend.training.avaliar_modelo import (
    localizar_arquivos_video,
    avaliar_video,
    salvar_resultados_csv,
    imprimir_relatorio_console
)


def test_localizar_arquivos_video_diretorio():
    """Valida varredura de arquivos de vídeo em um diretório."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        vid1 = tmp_path / "teste1.mp4"
        vid2 = tmp_path / "teste2.avi"
        txt1 = tmp_path / "notas.txt"

        vid1.write_text("dummy", encoding="utf-8")
        vid2.write_text("dummy", encoding="utf-8")
        txt1.write_text("dummy", encoding="utf-8")

        encontrados = localizar_arquivos_video(str(tmp_path))
        nomes = [p.name for p in encontrados]

        assert len(encontrados) == 2
        assert "teste1.mp4" in nomes
        assert "teste2.avi" in nomes
        assert "notas.txt" not in nomes


def test_salvar_resultados_csv():
    """Valida se o CSV é gerado corretamente com os cabeçalhos e valores formatados."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_csv = Path(tmpdir) / "relatorio.csv"

        resultados = [
            {
                "video": "video1.mp4",
                "caminho_completo": "/caminho/video1.mp4",
                "total_frames": 100,
                "frames_sem_deteccao": 10,
                "pct_frames_sem_deteccao": 10.0,
                "total_deteccoes": 150,
                "contagem_por_classe": {"Limite": 100, "Faixa_Pedestre": 50},
                "confianca_media_por_classe": {"Limite": 0.85, "Faixa_Pedestre": 0.90},
            }
        ]

        salvar_resultados_csv(resultados, output_csv)

        assert output_csv.exists()
        with open(output_csv, mode="r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 1
            row = reader[0]
            assert row["video"] == "video1.mp4"
            assert row["total_frames"] == "100"
            assert row["frames_sem_deteccao"] == "10"
            assert row["pct_frames_sem_deteccao"] == "10.00"
            assert row["total_deteccoes"] == "150"
            assert row["count_Limite"] == "100"
            assert row["conf_avg_Limite"] == "0.8500"


def test_avaliar_video_mocked_yolo():
    """Valida o cálculo de estatísticas (total frames, sem detecção, contagem e médias) com YOLO mockado."""
    mock_model = MagicMock()
    mock_model.names = {0: "Limite", 1: "Faixa_Pedestre"}

    # Mock do resultado da inferência para 2 frames: 1º frame com detecções, 2º frame vazio
    box1 = MagicMock()
    box1.cls = [MagicMock(item=lambda: 0)]
    box1.conf = [MagicMock(item=lambda: 0.80)]

    res1 = MagicMock()
    res1.boxes = [box1]

    res2 = MagicMock()
    res2.boxes = []

    mock_model.predict.side_effect = [[res1], [res2]]

    # Mock do cv2.VideoCapture para retornar 2 frames
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.side_effect = [
        (True, "dummy_frame_1"),
        (True, "dummy_frame_2"),
        (False, None)
    ]

    with patch("cv2.VideoCapture", return_value=mock_cap):
        stats = avaliar_video(
            model=mock_model,
            video_path=Path("video_teste_dummy.mp4"),
            conf_thresh=0.25
        )

    assert stats["total_frames"] == 2
    assert stats["frames_sem_deteccao"] == 1
    assert stats["pct_frames_sem_deteccao"] == 50.0
    assert stats["total_deteccoes"] == 1
    assert stats["contagem_por_classe"]["Limite"] == 1
    assert stats["contagem_por_classe"]["Faixa_Pedestre"] == 0
    assert pytest.approx(stats["confianca_media_por_classe"]["Limite"], 0.01) == 0.80
