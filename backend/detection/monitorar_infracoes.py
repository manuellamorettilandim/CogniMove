#!/usr/bin/env python3
"""
CogniMove — Monitor de Infrações em Tempo Real
Ponto de entrada principal (CLI).

Exemplos de uso:
  python monitorar_infracoes.py --source 0
  python monitorar_infracoes.py --source rtsp://192.168.1.10/stream
  python monitorar_infracoes.py --source ../videos_teste/video_teste.mp4 --janela
  python monitorar_infracoes.py --source 0 --preset caetano_alvares --dashboard
  python monitorar_infracoes.py --source video.mp4 --dashboard --porta 5000
"""
import os
import sys
import argparse
import threading
import queue
from pathlib import Path

# Garantir que detection/ está no path para imports absolutos
_HERE    = Path(__file__).resolve().parent   # detection/
_BACKEND = _HERE.parent                      # backend/
_ROOT    = _BACKEND.parent                   # Cognimove_Melissa/
sys.path.insert(0, str(_HERE))


def parse_args():
    p = argparse.ArgumentParser(
        description="CogniMove — Detecção de Infrações de Trânsito em Tempo Real",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--source", "-s", default=None,
        help="Fonte de vídeo: 0 (webcam), rtsp://..., ou caminho de arquivo."
             " Padrão: busca automática em videos_teste/",
    )
    p.add_argument(
        "--preset", "-p", default="general",
        help="Nome do preset de câmera em backend/calibration/presets/ (sem .json). "
             "Padrão: general",
    )
    p.add_argument(
        "--camera", "-c", default="Camera 1",
        help="Nome identificador da câmera (aparece no relatório). Padrão: 'Camera 1'",
    )
    p.add_argument(
        "--janela", "-j", action="store_true",
        help="Exibir janela OpenCV com o vídeo anotado (pressione Q para sair).",
    )
    p.add_argument(
        "--dashboard", "-d", action="store_true",
        help="Iniciar o dashboard web Flask em paralelo.",
    )
    p.add_argument(
        "--porta", type=int, default=5000,
        help="Porta do dashboard Flask. Padrão: 5000",
    )
    return p.parse_args()


def find_source(source_arg):
    """Resolve a fonte de vídeo: tenta numérico, depois busca arquivo."""
    if source_arg is not None:
        # Webcam por índice
        try:
            return int(source_arg)
        except ValueError:
            pass
        # Arquivo ou URL RTSP
        if os.path.isfile(source_arg):
            return os.path.abspath(source_arg)
        # Relativo à raiz do projeto
        candidates = [
            _ROOT / "videos_teste"   / source_arg,
            _ROOT / "videos_originais" / source_arg,
            _ROOT / source_arg,
        ]
        for c in candidates:
            if c.is_file():
                return str(c)
        # RTSP / câmera IP — retornar como string
        if source_arg.startswith(("rtsp://", "rtmp://", "http://", "https://")):
            return source_arg
        print(f"[Aviso] Fonte '{source_arg}' não encontrada como arquivo. "
              "Tentando abrir diretamente...")
        return source_arg

    # Busca automática em videos_teste/ e videos_originais/
    import glob
    search_dirs = [
        _ROOT / "videos_teste",
        _ROOT / "videos_originais",
    ]
    videos = []
    for d in search_dirs:
        for ext in ("*.mp4", "*.avi", "*.mov", "*.mkv"):
            videos.extend(d.glob(ext))
    if videos:
        videos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        chosen = str(videos[0])
        print(f"[Auto] Vídeo localizado: {chosen}")
        return chosen

    print("[Erro] Nenhuma fonte de vídeo encontrada. Use --source para especificar.")
    sys.exit(1)


def start_dashboard(frame_q, infracoes_q, port: int):
    """Inicializa o servidor Flask em uma thread separada."""
    frontend_dir = _ROOT / "frontend"
    sys.path.insert(0, str(frontend_dir))
    try:
        import app as flask_app
        flask_app.frame_queue     = frame_q
        flask_app.infracoes_queue = infracoes_q
        t = threading.Thread(
            target=lambda: flask_app.app.run(
                host="0.0.0.0", port=port,
                debug=False, use_reloader=False, threaded=True,
            ),
            daemon=True,
        )
        t.start()
        print(f"[Dashboard] Disponível em http://localhost:{port}")
    except Exception as e:
        print(f"[Aviso] Não foi possível iniciar o dashboard: {e}")


def main():
    args = parse_args()
    source = find_source(args.source)

    frame_q     = queue.Queue(maxsize=2)
    infracoes_q = queue.Queue(maxsize=200)

    if args.dashboard:
        start_dashboard(frame_q, infracoes_q, args.porta)

    # Importar detector após configurar o path
    from infracoes.detector import InfracaoDetector

    detector = InfracaoDetector(
        source          = source,
        preset_name     = args.preset,
        models_dir      = str(_BACKEND / "models"),
        output_dir      = str(_BACKEND / "outputs"),
        camera_name     = args.camera,
        show_window     = args.janela or not args.dashboard,
        frame_queue     = frame_q     if args.dashboard else None,
        infracoes_queue = infracoes_q if args.dashboard else None,
    )

    print("=" * 60)
    print(" COGNIMOVE — Sistema de Detecção de Infrações")
    print("=" * 60)
    print(f" Fonte:   {source}")
    print(f" Preset:  {args.preset}")
    print(f" Câmera:  {args.camera}")
    if args.dashboard:
        print(f" Dashboard: http://localhost:{args.porta}")
    print("=" * 60)

    try:
        detector.run()
    except KeyboardInterrupt:
        print("\n[Interrompido] Encerrando...")
        detector.stop()


if __name__ == "__main__":
    main()
