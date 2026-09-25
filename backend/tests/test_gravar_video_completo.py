"""
Testes Unitários — Gravação de Vídeo Completo Anotado (InfracaoDetector)

Valida que o argumento --salvar-video / --gravar-completo inicializa o cv2.VideoWriter,
grava os quadros anotados no diretório configurado (ex: videos_treinados/)
e finaliza o arquivo ao encerrar a execução.
"""
from __future__ import annotations

import os
import tempfile
import numpy as np
import pytest
from pathlib import Path

from backend.detection.infracoes.detector import InfracaoDetector
from backend.detection.monitorar_infracoes import parse_args


def test_infracao_detector_gravar_video_completo():
    """Garante que salvar_video=True gera um arquivo MP4 valido anotado."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_video_dir = Path(tmpdir) / "videos_treinados"
        
        detector = InfracaoDetector(
            source="0",
            preset_name="general",
            salvar_video=True,
            video_output_dir=output_video_dir,
            show_window=False,
        )

        # Executa a inicialização do setup
        width, height, fps = 640, 480, 30.0
        detector._setup(width, height, fps)

        assert detector.full_video_writer is not None
        assert detector.full_video_writer.isOpened()
        assert detector.full_video_path is not None

        # Processa 10 frames sintéticos
        dummy_frame = np.zeros((height, width, 3), dtype=np.uint8)
        for _ in range(10):
            annotated, _ = detector._process_frame(dummy_frame)
            detector.full_video_writer.write(annotated)

        # Libera o arquivo
        detector.full_video_writer.release()
        detector.full_video_writer = None

        # Valida que o arquivo foi salvo com sucesso e possui tamanho maior que zero
        assert os.path.exists(detector.full_video_path)
        assert os.path.getsize(detector.full_video_path) > 0
        assert detector.full_video_path.endswith(".mp4")


def test_cli_parse_args_salvar_video(monkeypatch):
    """Valida se a opção --salvar-video / --gravar-completo é reconhecida no CLI."""
    monkeypatch.setattr("sys.argv", ["monitorar_infracoes.py", "--salvar-video"])
    args = parse_args()
    assert args.salvar_video is True

    monkeypatch.setattr("sys.argv", ["monitorar_infracoes.py", "--gravar-completo"])
    args_alias = parse_args()
    assert args_alias.salvar_video is True
