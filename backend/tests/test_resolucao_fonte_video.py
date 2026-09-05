"""
Testes Unitários — Resolução de Caminhos de Vídeo no InfracaoDetector

Valida a busca automática em videos_teste/ e videos_originais/, além
do suporte a webcam numérica e URLs RTSP/HTTP.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from backend.detection.infracoes.detector import InfracaoDetector


def test_resolver_fonte_encontra_arquivo_em_videos_originais():
    """
    (3) Confirma que, dado um nome de arquivo que só existe em videos_originais/
    (e não em videos_teste/), a resolução encontra o arquivo corretamente.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        dir_teste = root / "videos_teste"
        dir_original = root / "videos_originais"
        dir_teste.mkdir()
        dir_original.mkdir()

        video_name = "cruzeiro_camera1.mp4"
        arquivo_original = dir_original / video_name
        arquivo_original.write_text("dummy video content", encoding="utf-8")

        # Não existe em videos_teste/
        assert not (dir_teste / video_name).exists()
        assert (dir_original / video_name).exists()

        resolvido = InfracaoDetector.resolver_fonte(video_name, root=root)
        assert resolvido == str(arquivo_original)


def test_resolver_fonte_prioridade_videos_teste_sobre_originais():
    """
    Garante que se o arquivo existir em ambas as pastas, videos_teste/ tem prioridade.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        dir_teste = root / "videos_teste"
        dir_original = root / "videos_originais"
        dir_teste.mkdir()
        dir_original.mkdir()

        video_name = "video_comum.mp4"
        arquivo_teste = dir_teste / video_name
        arquivo_original = dir_original / video_name
        arquivo_teste.write_text("teste content", encoding="utf-8")
        arquivo_original.write_text("original content", encoding="utf-8")

        resolvido = InfracaoDetector.resolver_fonte(video_name, root=root)
        assert resolvido == str(arquivo_teste)


def test_resolver_fonte_webcam_e_stream():
    """Valida resolução de inteiros, strings numéricas e URLs de streaming."""
    assert InfracaoDetector.resolver_fonte(0) == 0
    assert InfracaoDetector.resolver_fonte("0") == 0
    assert InfracaoDetector.resolver_fonte("1") == 1
    assert InfracaoDetector.resolver_fonte("rtsp://192.168.1.50/live") == "rtsp://192.168.1.50/live"
    assert InfracaoDetector.resolver_fonte("http://192.168.1.50:8080/video") == "http://192.168.1.50:8080/video"
