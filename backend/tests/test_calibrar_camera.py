"""
Testes Unitários — Ferramenta de Calibração de Câmera (Separação Faixa vs Retenção)

Valida que a ferramenta de calibração separa corretamente Linha de Faixa (L)
de Linha de Retenção Semafórica (R), gerando presets JSON não-duplicados.
"""
from __future__ import annotations

import cv2
import json
import tempfile
from pathlib import Path
import pytest

from backend.calibration.calibrar_camera import CalibradorCamera


def test_cliques_modo_line_alimentam_lines():
    """
    (9.a) Simula 2 cliques no modo 'line' e valida que a linha é adicionada a self.lines.
    """
    cal = CalibradorCamera(source=0, preset_name="teste_faixa", output_dir=Path("/tmp"))
    cal.mode = "line"

    # Clique 1: ponto inicial (100, 200)
    cal._on_mouse(cv2.EVENT_LBUTTONDOWN, 100, 200, 0, None)
    assert len(cal.current_pts) == 1
    assert len(cal.lines) == 0

    # Clique 2: ponto final (300, 200) -> fecha a linha
    cal._on_mouse(cv2.EVENT_LBUTTONDOWN, 300, 200, 0, None)
    assert len(cal.current_pts) == 0
    assert len(cal.lines) == 1
    assert cal.lines[0] == [[100, 200], [300, 200]]
    assert len(cal.stop_lines) == 0


def test_cliques_modo_stop_line_alimentam_stop_lines():
    """
    (9.b) Simula 2 cliques no modo 'stop_line' e valida que a linha é adicionada a self.stop_lines.
    """
    cal = CalibradorCamera(source=0, preset_name="teste_retencao", output_dir=Path("/tmp"))
    cal.mode = "stop_line"

    # Clique 1: (50, 150)
    cal._on_mouse(cv2.EVENT_LBUTTONDOWN, 50, 150, 0, None)
    assert len(cal.current_pts) == 1
    assert len(cal.stop_lines) == 0

    # Clique 2: (450, 150) -> fecha a linha de retenção
    cal._on_mouse(cv2.EVENT_LBUTTONDOWN, 450, 150, 0, None)
    assert len(cal.current_pts) == 0
    assert len(cal.stop_lines) == 1
    assert cal.stop_lines[0] == [[50, 150], [450, 150]]
    assert len(cal.lines) == 0


def test_save_gera_json_com_lines_e_stop_lines_distintos():
    """
    (9.c) Configura lines e stop_lines com coordenadas diferentes e valida
    que o preset JSON salvo contém estruturas independentes e não duplicadas.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        preset_name = "cruzamento_calibrado"
        cal = CalibradorCamera(source=0, preset_name=preset_name, output_dir=out_dir)

        # Configura geometrias distintas
        linha_faixa = [[100, 200], [300, 200]]
        linha_retencao = [[100, 250], [300, 250]]

        cal.lines = [linha_faixa]
        cal.stop_lines = [linha_retencao]

        preset_file = cal._save(width=1280, height=720)
        assert preset_file.exists()

        with open(preset_file, "r", encoding="utf-8") as f:
            dados = json.load(f)

        assert "lines" in dados
        assert "stop_lines" in dados

        assert len(dados["lines"]) == 1
        assert len(dados["stop_lines"]) == 1

        # Conteúdo deve ser estritamente diferente
        assert dados["lines"][0]["pt1"] == [100, 200]
        assert dados["lines"][0]["pt2"] == [300, 200]

        assert dados["stop_lines"][0]["pt1"] == [100, 250]
        assert dados["stop_lines"][0]["pt2"] == [300, 250]

        assert dados["lines"] != dados["stop_lines"]


def test_calibrador_camera_resolve_fonte_em_videos_originais(monkeypatch):
    """
    (4) Confirma que CalibradorCamera consegue resolver um nome de arquivo
    que só existe em videos_originais/ (e não em videos_teste/).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        dir_originais = root / "videos_originais"
        dir_teste = root / "videos_teste"
        dir_originais.mkdir()
        dir_teste.mkdir()

        video_name = "camera_cruzamento_novo.mp4"
        arquivo_video = dir_originais / video_name
        arquivo_video.write_text("dummy video", encoding="utf-8")

        cal = CalibradorCamera(source=video_name, preset_name="teste_resolucao", output_dir=root)

        captured_source = []

        class MockVideoCapture:
            def __init__(self, src):
                captured_source.append(src)

            def isOpened(self):
                return True

            def get(self, prop):
                return 100

            def set(self, prop, val):
                pass

            def read(self):
                import numpy as np
                return True, np.zeros((100, 100, 3), dtype=np.uint8)

            def release(self):
                pass

        monkeypatch.setattr("backend.calibration.calibrar_camera.cv2.VideoCapture", MockVideoCapture)
        monkeypatch.setattr("backend.calibration.calibrar_camera._ROOT", root)

        frame = cal._grab_frame()
        assert frame is not None
        assert len(captured_source) == 1
        assert captured_source[0] == str(arquivo_video)


def test_save_preset_existente_cancelado_quando_usuario_recusa(monkeypatch):
    """
    (4.a) Valida que _save() cancela a gravação e preserva o arquivo existente
    quando a confirmação do usuário for negativa ('n').
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        preset_name = "preset_duplicado"
        arquivo_preset = out_dir / f"{preset_name}.json"
        arquivo_preset.write_text('{"versao": "original"}', encoding="utf-8")

        cal = CalibradorCamera(source=0, preset_name=preset_name, output_dir=out_dir)
        cal.lines = [[[10, 10], [20, 20]]]

        monkeypatch.setattr("builtins.input", lambda prompt: "n")

        retorno = cal._save(width=1280, height=720)
        assert retorno is None
        assert arquivo_preset.read_text(encoding="utf-8") == '{"versao": "original"}'


def test_save_preset_existente_cria_backup_e_sobrescreve_com_confirmacao(monkeypatch):
    """
    (4.b) Valida que _save() cria cópia de backup com timestamp e sobrescreve
    o preset quando a confirmação do usuário for positiva ('s').
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        preset_name = "preset_duplicado"
        arquivo_preset = out_dir / f"{preset_name}.json"
        arquivo_preset.write_text('{"versao": "original"}', encoding="utf-8")

        cal = CalibradorCamera(source=0, preset_name=preset_name, output_dir=out_dir)
        cal.lines = [[[10, 10], [20, 20]]]

        monkeypatch.setattr("builtins.input", lambda prompt: "s")

        retorno = cal._save(width=1280, height=720)
        assert retorno == arquivo_preset

        # Verifica se o arquivo foi atualizado
        dados_salvos = json.loads(arquivo_preset.read_text(encoding="utf-8"))
        assert "lines" in dados_salvos
        assert len(dados_salvos["lines"]) == 1

        # Verifica se o backup foi criado com o conteúdo anterior
        backups = list(out_dir.glob(f"{preset_name}.json.bak.*"))
        assert len(backups) == 1
        assert backups[0].read_text(encoding="utf-8") == '{"versao": "original"}'


