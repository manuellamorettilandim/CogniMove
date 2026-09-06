"""
Testes Unitários — Utilitário de Limpeza de Evidências (limpeza.py)

Valida a identificação e remoção de arquivos antigos com base no tempo de modificação (st_mtime),
incluindo o funcionamento do modo simulação (--dry-run).
"""
import os
import time
import tempfile
from pathlib import Path

from backend.detection.limpeza import limpar_evidencias_antigas
from backend.detection.infracoes.evidencias import limpar_evidencias_antigas as limpar_evidencias_reexportado


def test_limpar_evidencias_antigas_remocao():
    """Confirma que arquivos antigos (> dias_retencao) são removidos e recentes mantidos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 1. Criar subdiretórios estilo evidencias/
        sub_screenshots = tmp_path / "screenshots"
        sub_clips = tmp_path / "clips"
        sub_screenshots.mkdir()
        sub_clips.mkdir()

        # 2. Criar arquivo recente (mtime = agora)
        arq_recente = sub_screenshots / "recente_2026.jpg"
        arq_recente.write_text("conteudo recente", encoding="utf-8")

        # 3. Criar arquivos antigos (mtime = agora - 40 dias)
        arq_antigo_1 = sub_screenshots / "antigo_2026.jpg"
        arq_antigo_2 = sub_clips / "antigo_2026.mp4"
        arq_antigo_1.write_text("conteudo antigo 1", encoding="utf-8")
        arq_antigo_2.write_text("conteudo antigo 2", encoding="utf-8")

        agora = time.time()
        mtime_antigo = agora - (40 * 86400)  # 40 dias atrás

        os.utime(arq_antigo_1, (mtime_antigo, mtime_antigo))
        os.utime(arq_antigo_2, (mtime_antigo, mtime_antigo))

        # 4. Executar limpeza com retenção de 30 dias
        removidos = limpar_evidencias_antigas(tmp_path, dias_retencao=30, dry_run=False)

        assert removidos == 2
        assert arq_recente.exists()
        assert not arq_antigo_1.exists()
        assert not arq_antigo_2.exists()


def test_limpar_evidencias_dry_run():
    """Valida se o modo dry_run=True identifica os arquivos antigos sem deletá-los."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        arq_antigo = tmp_path / "arquivo_antigo.jpg"
        arq_antigo.write_text("conteudo antigo", encoding="utf-8")

        mtime_antigo = time.time() - (45 * 86400)
        os.utime(arq_antigo, (mtime_antigo, mtime_antigo))

        removidos_simulados = limpar_evidencias_antigas(tmp_path, dias_retencao=30, dry_run=True)

        assert removidos_simulados == 1
        # O arquivo NÃO deve ter sido deletado
        assert arq_antigo.exists()


def test_limpar_evidencias_reexportado():
    """Valida a reexportação da função a partir de backend.detection.infracoes.evidencias."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        arq = tmp_path / "teste.jpg"
        arq.write_text("dummy", encoding="utf-8")
        mtime_antigo = time.time() - (50 * 86400)
        os.utime(arq, (mtime_antigo, mtime_antigo))

        res = limpar_evidencias_reexportado(tmp_path, dias_retencao=30, dry_run=False)
        assert res == 1
        assert not arq.exists()
