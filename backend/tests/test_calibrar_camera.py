"""
Testes Unitários — Ferramenta de Calibração de Câmera (backend/calibration/calibrar_camera.py)

Valida o funcionamento isolado do CalibradorCamera sem abrir janelas OpenCV:
- Tratamento de eventos de clique do mouse em _on_mouse() (linhas, retenções, polígonos)
- Serialização e estrutura do JSON gerado em _save()
- Proteção contra sobrescrita acidental e geração de backups
- Remoção da última forma via tecla X
- Detecção geométrica de polígonos autointersectantes
"""
from __future__ import annotations

import cv2
import json
import tempfile
from pathlib import Path
import pytest

from backend.calibration.calibrar_camera import CalibradorCamera, polygon_is_self_intersecting


def test_on_mouse_linha_completa_com_dois_pontos():
    """
    (1.a) Simula dois cliques esquerdos no modo 'line' e valida que a linha é
    adicionada a self.lines com os 2 pontos corretos, e que self.current_pts foi limpo.
    """
    cal = CalibradorCamera(source=0, preset_name="teste_faixa", output_dir=Path("/tmp"))
    cal.mode = "line"

    # Clique 1: ponto inicial (100, 200)
    cal._on_mouse(cv2.EVENT_LBUTTONDOWN, 100, 200, 0, None)
    assert len(cal.current_pts) == 1
    assert cal.current_pts[0] == [100, 200]
    assert len(cal.lines) == 0

    # Clique 2: ponto final (300, 200) -> fecha a linha automaticamente
    cal._on_mouse(cv2.EVENT_LBUTTONDOWN, 300, 200, 0, None)
    assert len(cal.current_pts) == 0
    assert len(cal.lines) == 1
    assert cal.lines[0] == [[100, 200], [300, 200]]
    assert len(cal.stop_lines) == 0


def test_on_mouse_poligono_fecha_com_clique_direito():
    """
    (1.b) Simula 4 cliques esquerdos seguidos de 1 clique direito no modo 'polygon'
    e confirma que um polígono de 4 pontos foi adicionado a self.polygons e self.current_pts limpo.
    """
    cal = CalibradorCamera(source=0, preset_name="teste_poligono", output_dir=Path("/tmp"))
    cal.mode = "polygon"

    pontos_esperados = [[10, 10], [100, 10], [100, 100], [10, 100]]
    for x, y in pontos_esperados:
        cal._on_mouse(cv2.EVENT_LBUTTONDOWN, x, y, 0, None)

    assert len(cal.current_pts) == 4
    assert len(cal.polygons) == 0

    # Clique direito para fechar o polígono
    cal._on_mouse(cv2.EVENT_RBUTTONDOWN, 0, 0, 0, None)
    assert len(cal.current_pts) == 0
    assert len(cal.polygons) == 1
    assert cal.polygons[0] == pontos_esperados


def test_save_gera_estrutura_json_esperada():
    """
    (1.c) Instancia CalibradorCamera com linhas, retenções, polígonos e cruzamentos conhecidos,
    chama _save() em diretório temporário e confirma que todos os campos esperados estão no JSON.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        preset_name = "preset_completo"
        cal = CalibradorCamera(source=0, preset_name=preset_name, output_dir=out_dir)

        cal.lines = [[[10, 20], [30, 40]]]
        cal.stop_lines = [[[50, 60], [70, 80]]]
        cal.polygons = [[[100, 100], [200, 100], [200, 200], [100, 200]]]
        cal.intersections = [[[300, 300], [400, 300], [400, 400], [300, 400]]]

        ref_w, ref_h = 1920, 1080
        out_file = cal._save(width=ref_w, height=ref_h)
        assert out_file is not None
        assert out_file.exists()

        with open(out_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["name"] == preset_name
        assert data["ref_width"] == ref_w
        assert data["ref_height"] == ref_h

        # Valida linhas de faixa
        assert len(data["lines"]) == 1
        assert data["lines"][0]["pt1"] == [10, 20]
        assert data["lines"][0]["pt2"] == [30, 40]

        # Valida linhas de retenção
        assert len(data["stop_lines"]) == 1
        assert data["stop_lines"][0]["pt1"] == [50, 60]
        assert data["stop_lines"][0]["pt2"] == [70, 80]

        # Valida polígonos (bike box)
        assert len(data["polygons"]) == 1
        assert data["polygons"][0]["points"] == cal.polygons[0]
        assert data["polygons"][0]["type"] == "bike_box"

        # Valida polígonos de cruzamento
        assert len(data["intersection_polygons"]) == 1
        assert data["intersection_polygons"][0]["points"] == cal.intersections[0]
        assert data["intersection_polygons"][0]["type"] == "intersection"


def test_save_nao_sobrescreve_sem_confirmacao(monkeypatch):
    """
    (1.d) Confirma que chamar _save() duas vezes com o mesmo preset_name, mockando input()
    para retornar 'n' na segunda vez, preserva o conteúdo do primeiro arquivo salvo.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        preset_name = "camera_praca"
        cal = CalibradorCamera(source=0, preset_name=preset_name, output_dir=out_dir)

        cal.lines = [[[1, 1], [2, 2]]]
        arquivo_primeiro = cal._save(width=1280, height=720)
        assert arquivo_primeiro.exists()
        conteudo_original = arquivo_primeiro.read_text(encoding="utf-8")

        # Altera geometrias na memória e tenta salvar novamente recusando confirmação
        cal.lines = [[[99, 99], [100, 100]]]
        monkeypatch.setattr("builtins.input", lambda prompt: "n")

        retorno = cal._save(width=1280, height=720)
        assert retorno is None
        assert arquivo_primeiro.read_text(encoding="utf-8") == conteudo_original


def test_cliques_modo_stop_line_alimentam_stop_lines():
    """
    Simula 2 cliques no modo 'stop_line' e valida que a linha é adicionada a self.stop_lines.
    """
    cal = CalibradorCamera(source=0, preset_name="teste_retencao", output_dir=Path("/tmp"))
    cal.mode = "stop_line"

    cal._on_mouse(cv2.EVENT_LBUTTONDOWN, 50, 150, 0, None)
    assert len(cal.current_pts) == 1
    assert len(cal.stop_lines) == 0

    cal._on_mouse(cv2.EVENT_LBUTTONDOWN, 450, 150, 0, None)
    assert len(cal.current_pts) == 0
    assert len(cal.stop_lines) == 1
    assert cal.stop_lines[0] == [[50, 150], [450, 150]]
    assert len(cal.lines) == 0


def test_save_preset_existente_cria_backup_e_sobrescreve_com_confirmacao(monkeypatch):
    """
    Valida que _save() cria cópia de backup com timestamp e sobrescreve
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

        dados_salvos = json.loads(arquivo_preset.read_text(encoding="utf-8"))
        assert "lines" in dados_salvos
        assert len(dados_salvos["lines"]) == 1

        backups = list(out_dir.glob(f"{preset_name}.json.bak.*"))
        assert len(backups) == 1
        assert backups[0].read_text(encoding="utf-8") == '{"versao": "original"}'


def test_calibrador_camera_resolve_fonte_em_videos_originais(monkeypatch):
    """
    Confirma que CalibradorCamera consegue resolver um nome de arquivo
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


def test_remover_ultima_forma_tecla_x():
    """
    Valida que a remoção da última forma (remover_ultima_forma)
    remove apenas o último elemento da lista do modo ativo, preservando os anteriores.
    """
    cal = CalibradorCamera(source=0, preset_name="teste_remover", output_dir=Path("/tmp"))

    # 1. Modo line
    cal.mode = "line"
    linha_1 = [[10, 10], [20, 20]]
    linha_2 = [[30, 30], [40, 40]]
    cal.lines = [linha_1, linha_2]

    removido = cal.remover_ultima_forma()
    assert removido == linha_2
    assert len(cal.lines) == 1
    assert cal.lines[0] == linha_1

    # 2. Modo stop_line
    cal.mode = "stop_line"
    ret_1 = [[50, 50], [60, 60]]
    ret_2 = [[70, 70], [80, 80]]
    cal.stop_lines = [ret_1, ret_2]

    removido_ret = cal.remover_ultima_forma()
    assert removido_ret == ret_2
    assert len(cal.stop_lines) == 1
    assert cal.stop_lines[0] == ret_1

    # 3. Modo vazio
    cal.mode = "polygon"
    assert cal.remover_ultima_forma() is None


def test_polygon_self_intersecting_detection_and_warning():
    """
    Valida a detecção de autointerseção em polígonos:
    1. Polígono em formato de '8' / borboleta deve ser identificado como autointersectante (True).
    2. Polígono simples (retângulo) NÃO deve ser identificado como autointersectante (False).
    3. Simula fechamento de polígono em _on_mouse() e verifica o aviso visual warning_msg.
    """
    poly_figura_8 = [[0, 0], [10, 10], [0, 10], [10, 0]]
    assert polygon_is_self_intersecting(poly_figura_8) is True

    poly_retangulo = [[0, 0], [10, 0], [10, 10], [0, 10]]
    assert polygon_is_self_intersecting(poly_retangulo) is False

    poly_triangulo = [[0, 0], [10, 0], [5, 10]]
    assert polygon_is_self_intersecting(poly_triangulo) is False

    cal = CalibradorCamera(source=0, preset_name="teste_warning", output_dir=Path("/tmp"))
    cal.mode = "polygon"

    # Polígono em 8
    cal.current_pts = list(poly_figura_8)
    cal._on_mouse(cv2.EVENT_RBUTTONDOWN, 0, 0, 0, None)
    assert len(cal.polygons) == 1
    assert cal.warning_msg is not None
    assert "autointersectante" in cal.warning_msg

    # Polígono válido
    cal.current_pts = list(poly_retangulo)
    cal._on_mouse(cv2.EVENT_RBUTTONDOWN, 0, 0, 0, None)
    assert len(cal.polygons) == 2
    assert cal.warning_msg is None
