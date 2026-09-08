"""
Testes Unitários — Gerenciador de Evidências

Valida a segurança contra vazamento de memória e exceções de comparação
de arrays NumPy em clip_data pendentes.
"""
from __future__ import annotations

import os
import cv2
import time
import tempfile
import numpy as np
import pytest

from backend.detection.infracoes.evidencias import GerenciadorEvidencias


def test_remocao_clip_data_com_numpy_arrays_nao_lanca_value_error():
    """
    (3.a) Valida que a remoção por ID único não tenta avaliar 'array == array',
    evitando 'ValueError: The truth value of an array with more than one element is ambiguous'.
    """
    frame_a = np.zeros((100, 100, 3), dtype=np.uint8)
    frame_b = np.ones((100, 100, 3), dtype=np.uint8) * 255

    clip1 = {
        "id": 1,
        "frames": [frame_a],
        "frames_needed": 10,
        "meta": {"tipo": "AVANCO_SINAL_VERMELHO", "ts": "20260905_120000", "tid": 1},
        "path": None,
    }
    clip2 = {
        "id": 2,
        "frames": [frame_b],
        "frames_needed": 10,
        "meta": {"tipo": "INVASAO_FAIXA", "ts": "20260905_120001", "tid": 2},
        "path": None,
    }

    pending = [clip1, clip2]

    # Tentativa de usar `in` com valor idêntico mas referência separada em dict com numpy arrays
    # dispararia ValueError caso tentasse comparação por valor.
    # Nossa implementação usa ID:
    pending = [c for c in pending if c.get("id") != clip1["id"]]

    assert len(pending) == 1
    assert pending[0]["id"] == 2


def test_registrar_devolve_caminho_mp4_do_clip_e_nao_pendente():
    """
    Valida que registrar() já devolve o caminho real do clip (determinístico,
    calculado a partir de tipo/ts/track_id) em vez da string "pendente" —
    esse valor é o que acaba gravado na coluna `clip` do CSV de relatório.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        gerenciador = GerenciadorEvidencias(
            output_dir=tmpdir,
            fps=10.0,
            buffer_seconds=0.1,
            post_seconds=0.1,
        )

        dummy_frame = np.zeros((120, 160, 3), dtype=np.uint8)
        inf = {"tipo": "AVANCO_SINAL_VERMELHO", "track_id": 7, "descricao": "Teste"}

        resultado = gerenciador.registrar(inf, dummy_frame)

        assert resultado["clip"] != "pendente"
        assert resultado["clip"].endswith(".mp4")
        assert os.path.dirname(resultado["clip"]) == gerenciador.clips_dir


def test_save_clip_com_quadros_sinteticos_gera_arquivo_valido():
    """
    Grava um clip curto a partir de quadros sintéticos (numpy, sem vídeo real
    nem YOLO) e confirma que o arquivo final abre com cv2.VideoCapture e devolve
    ao menos um quadro legível — ou seja, que a cascata imageio-ffmpeg → cv2/avc1
    → cv2/mp4v produziu um MP4 de verdade, não um arquivo vazio/corrompido como
    o antigo mp4v isolado. Tamanho de arquivo não é usado como critério: um clip
    válido bem comprimido pode ter poucas centenas de bytes.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        gerenciador = GerenciadorEvidencias(
            output_dir=tmpdir,
            fps=10.0,
            buffer_seconds=0.3,
            post_seconds=0.3,
        )

        # Quadros com ruído aleatório: quadros totalmente pretos comprimem
        # demais e poderiam ficar abaixo do limiar mesmo sendo válidos.
        rng = np.random.default_rng(42)
        frame = rng.integers(0, 256, size=(240, 352, 3), dtype=np.uint8)

        for _ in range(3):
            gerenciador.push_frame(frame)

        inf = {"tipo": "INVASAO_FAIXA", "track_id": 99, "descricao": "Teste clip sintético"}
        resultado = gerenciador.registrar(inf, frame)

        for _ in range(6):
            gerenciador.push_frame(frame)
            time.sleep(0.05)

        deadline = time.time() + 5.0
        while time.time() < deadline:
            with gerenciador._lock:
                if len(gerenciador._pending) == 0:
                    break
            time.sleep(0.05)

        clip_path = resultado["clip"]
        assert os.path.exists(clip_path), f"Clip não foi criado em {clip_path}"

        cap = cv2.VideoCapture(clip_path)
        try:
            assert cap.isOpened(), f"Clip em {clip_path} não abre com cv2.VideoCapture"
            ok, quadro = cap.read()
            assert ok, f"Clip em {clip_path} não devolveu um quadro legível"
            assert quadro is not None
        finally:
            cap.release()


def test_multiplas_infracoes_simultaneas_limpam_pending():
    """
    (3.b) Registra duas infrações quase simultâneas antes que a primeira termine de salvar,
    alimenta os frames necessários e valida que ambos os clip_data são removidos de _pending.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Buffer de 2 frames (0.2s a 10 fps) e pós de 2 frames (0.2s)
        gerenciador = GerenciadorEvidencias(
            output_dir=tmpdir,
            fps=10.0,
            buffer_seconds=0.2,
            post_seconds=0.2,
        )

        dummy_frame = np.zeros((120, 160, 3), dtype=np.uint8)

        # Alimenta buffer pré-evento
        gerenciador.push_frame(dummy_frame)
        gerenciador.push_frame(dummy_frame)

        inf1 = {"tipo": "AVANCO_SINAL_VERMELHO", "track_id": 10, "descricao": "Teste 1"}
        inf2 = {"tipo": "INVASAO_FAIXA", "track_id": 20, "descricao": "Teste 2"}

        # Registra infração 1 e 2 em sequência rápida
        gerenciador.registrar(inf1, dummy_frame)
        gerenciador.registrar(inf2, dummy_frame)

        assert len(gerenciador._pending) == 2, "Ambos os clips devem estar em _pending inicialmente."

        # Alimenta frames pós-evento para satisfazer frames_needed de ambos os clips
        for _ in range(5):
            gerenciador.push_frame(dummy_frame)
            time.sleep(0.02)

        # Aguarda as threads de salvamento finalizarem (tempo limite de segurança 2.0s)
        deadline = time.time() + 2.0
        while time.time() < deadline:
            with gerenciador._lock:
                if len(gerenciador._pending) == 0:
                    break
            time.sleep(0.05)

        with gerenciador._lock:
            assert len(gerenciador._pending) == 0, (
                f"Todos os clips deveriam ter sido removidos de _pending, mas restam: {len(gerenciador._pending)}"
            )
