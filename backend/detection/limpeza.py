"""
CogniMove — Utilitário de Limpeza e Manutenção de Evidências e Relatórios Antigos

Remove arquivos de evidências (screenshots, mini-clips) e relatórios mais antigos
que um número especificado de dias de retenção para evitar o esgotamento do disco.
"""
from __future__ import annotations
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def limpar_evidencias_antigas(
    diretorio: Path | str,
    dias_retencao: int = 30,
    dry_run: bool = False
) -> int:
    """
    Remove arquivos no diretório especificado (e subdiretórios) mais antigos que `dias_retencao` dias.

    Args:
        diretorio: Caminho do diretório contendo arquivos (ex: backend/outputs/evidencias).
        dias_retencao: Número de dias de retenção (arquivos com mtime > dias_retencao serão removidos).
        dry_run: Se True, simula a execução sem deletar os arquivos.

    Returns:
        Quantidade de arquivos removidos (ou identificados para remoção se dry_run=True).
    """
    dir_path = Path(diretorio)
    if not dir_path.exists() or not dir_path.is_dir():
        logging.warning(f"Diretório não localizado para limpeza: {dir_path}")
        return 0

    agora = time.time()
    limite_segundos = dias_retencao * 86400
    removidos = 0

    for arquivo in dir_path.rglob("*"):
        if arquivo.is_file():
            try:
                mtime = arquivo.stat().st_mtime
                idade_segundos = agora - mtime
                if idade_segundos > limite_segundos:
                    idade_dias = idade_segundos / 86400
                    if dry_run:
                        logging.info(f"[DRY-RUN] Seria removido: {arquivo.name} (idade: {idade_dias:.1f} dias)")
                    else:
                        arquivo.unlink()
                        logging.info(f"[REMOVIDO] Arquivo apagado: {arquivo.name} (idade: {idade_dias:.1f} dias)")
                    removidos += 1
            except OSError as e:
                logging.error(f"Erro ao processar arquivo {arquivo}: {e}")

    return removidos
