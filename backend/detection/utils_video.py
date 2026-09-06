"""
CogniMove — Utilitários de Resolução de Fontes de Vídeo
Centraliza a lógica de busca e resolução de arquivos de vídeo, webcams e streams.
"""
from __future__ import annotations

from pathlib import Path

_HERE = Path(__file__).resolve().parent      # detection/
_BACKEND = _HERE.parent                      # backend/
_DEFAULT_ROOT = _BACKEND.parent              # COGNIMOVE/


def resolver_fonte_video(source: str | int | float, root: Path | None = None) -> str | int:
    """Resolve a fonte de vídeo (webcam numérica, URL de stream ou arquivo local).

    Ordem de busca para arquivos:
      1. Caminho absoluto existente
      2. Relativo à raiz do projeto (root / p)
      3. Dentro de videos_teste/ (root / "videos_teste" / p.name)
      4. Dentro de videos_originais/ (root / "videos_originais" / p.name)
      5. Se não encontrado, retorna a string original como fallback.
    """
    if root is None:
        root = _DEFAULT_ROOT

    if isinstance(source, str):
        src_str = source.strip()
        if src_str.isdigit():
            return int(src_str)
        if src_str.startswith(("rtsp://", "rtmp://", "http://", "https://")):
            return src_str
        p = Path(src_str)
        if p.is_absolute() and p.exists():
            return str(p)
        if (root / p).exists():
            return str(root / p)
        if (root / "videos_teste" / p.name).exists():
            return str(root / "videos_teste" / p.name)
        if (root / "videos_originais" / p.name).exists():
            return str(root / "videos_originais" / p.name)
        return src_str

    if isinstance(source, (int, float)):
        return int(source)

    return source
