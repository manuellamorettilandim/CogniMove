"""
Testes Unitários — Gerenciador de Relatório (JSON Lines & CSV)

Valida a gravação eficiente O(1) em modo append via JSON Lines (.jsonl),
a reconstrução a partir do disco e a exportação para JSON tradicional.
"""
from __future__ import annotations

import json
import os
import tempfile
import pytest

from backend.detection.infracoes.relatorio import GerenciadorRelatorio


def test_relatorio_gravacao_json_lines_50_registros():
    """
    (5) Registra 50 infrações e valida que o arquivo final .jsonl contém
    exatamente 50 linhas JSON independentes (modo append sem reescrita total).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        rel = GerenciadorRelatorio(tmpdir, camera_name="Camera 50x")

        for i in range(50):
            infracao = {
                "tipo": "AVANCO_SINAL_VERMELHO" if i % 2 == 0 else "INVASAO_FAIXA",
                "descricao": f"Infração número {i}",
                "track_id": i + 1,
                "classe": "Carro",
                "confianca": 0.85 + (i % 10) * 0.01,
                "frame": i * 30,
                "timestamp": f"2026-09-05T12:{i:02d}:00",
            }
            evidencias = {
                "screenshot": f"screenshot_{i}.jpg",
                "clip": f"clip_{i}.mp4",
            }
            analise = {
                "causa_principal": "Tempo semafórico inadequado",
                "confianca": 0.35,
                "fatores_ativos": ["chuva_forte"],
                "distribuicao": {"Tempo semafórico inadequado": 0.35, "Congestionamento": 0.25},
            }
            rel.adicionar(infracao, evidencias, analise)

        # 1. Validação em memória
        records_mem = rel.get_records()
        assert len(records_mem) == 50

        # 2. Validação direta do arquivo no disco (.jsonl)
        assert os.path.exists(rel.jsonl_path)
        with open(rel.jsonl_path, "r", encoding="utf-8") as f:
            linhas = [linha.strip() for linha in f if linha.strip()]

        assert len(linhas) == 50, f"O arquivo .jsonl deveria conter 50 linhas, mas tem {len(linhas)}."

        # Cada linha deve ser um JSON válido individual
        for idx, linha in enumerate(linhas):
            obj = json.loads(linha)
            assert obj["track_id"] == idx + 1
            assert obj["camera"] == "Camera 50x"

        # 3. Validação de reconstrução a partir do disco
        records_disk = rel.get_records(from_disk=True)
        assert len(records_disk) == 50
        assert records_disk[0]["descricao"] == "Infração número 0"
        assert records_disk[-1]["descricao"] == "Infração número 49"


def test_relatorio_carregar_jsonl_e_exportar_json_tradicional():
    """Valida funções auxiliares de carregamento estático e exportação para JSON tradicional."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rel = GerenciadorRelatorio(tmpdir, camera_name="Cam Export")
        rel.adicionar({"tipo": "BLOQUEIO_CRUZAMENTO", "track_id": 99, "descricao": "Cruzamento bloqueado"})

        # Teste carregar_jsonl estático
        carregados = GerenciadorRelatorio.carregar_jsonl(rel.jsonl_path)
        assert len(carregados) == 1
        assert carregados[0]["tipo"] == "BLOQUEIO_CRUZAMENTO"

        # Teste exportar_json_tradicional
        json_trad_path = rel.exportar_json_tradicional()
        assert os.path.exists(json_trad_path)
        with open(json_trad_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["track_id"] == 99
