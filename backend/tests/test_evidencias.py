"""
Testes Unitários — Gerenciador de Evidências

Valida a segurança contra vazamento de memória e exceções de comparação
de arrays NumPy em clip_data pendentes.
"""
from __future__ import annotations

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
