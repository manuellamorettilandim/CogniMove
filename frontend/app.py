"""
CogniMove — Dashboard Web (Flask)
Streaming MJPEG + SSE para infrações em tempo real.

Uso standalone:
  python app.py --source 0 --preset caetano_alvares

Uso via monitorar_infracoes.py:
  python ../backend/detection/monitorar_infracoes.py --source 0 --dashboard
"""
from __future__ import annotations
import os, sys, json, queue, threading, argparse
from pathlib import Path
from flask import (Flask, render_template, Response, jsonify,
                   request, stream_with_context, send_from_directory)

_FRONTEND = Path(__file__).resolve().parent
_ROOT     = _FRONTEND.parent
_BACKEND  = _ROOT / "backend"
_DETECT   = _BACKEND / "detection"

sys.path.insert(0, str(_DETECT))

app = Flask(__name__, template_folder="templates", static_folder="static")

# ── Estado compartilhado (injetado por monitorar_infracoes.py ou criado aqui) ─
frame_queue:     queue.Queue = queue.Queue(maxsize=2)
infracoes_queue: queue.Queue = queue.Queue(maxsize=500)
detector = None
detector_thread: threading.Thread | None = None


# ── Rotas principais ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    """Stream MJPEG do vídeo anotado."""
    def generate():
        while True:
            try:
                frame_bytes = frame_queue.get(timeout=1.5)
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" +
                       frame_bytes + b"\r\n")
            except queue.Empty:
                # Frame de espera (logo CogniMove)
                continue
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/events")
def api_events():
    """SSE: envia infrações em tempo real para o dashboard."""
    def stream():
        while True:
            try:
                inf = infracoes_queue.get(timeout=2.0)
                payload = json.dumps(inf, ensure_ascii=False, default=str)
                yield f"data: {payload}\n\n"
            except queue.Empty:
                yield "data: {\"ping\":true}\n\n"
    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/stats")
def api_stats():
    if detector:
        return jsonify(detector.stats)
    return jsonify({"total": 0, "AVANCO_SINAL_VERMELHO": 0,
                    "INVASAO_FAIXA": 0, "BLOQUEIO_CRUZAMENTO": 0})


@app.route("/api/relatorio")
def api_relatorio():
    if detector and detector.relatorio:
        return jsonify(detector.relatorio.get_records())
    return jsonify([])


@app.route("/api/relatorio/csv")
def api_relatorio_csv():
    """Download do CSV da sessão."""
    if detector and detector.relatorio:
        csv_path = Path(detector.relatorio.csv_path)
        return send_from_directory(csv_path.parent, csv_path.name,
                                   as_attachment=True)
    return "Relatório não disponível", 404


@app.route("/api/status")
def api_status():
    running = detector_thread is not None and detector_thread.is_alive()
    return jsonify({"running": running,
                    "source":  str(detector.source) if detector else None})


@app.route("/api/videos")
def api_videos():
    """Retorna lista de vídeos disponíveis na pasta videos_teste."""
    vt_dir = _ROOT / "videos_teste"
    videos = []
    if vt_dir.exists():
        for f in sorted(vt_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in ('.mp4', '.avi', '.mkv', '.mov'):
                videos.append({
                    "filename": f.name,
                    "path": f"videos_teste/{f.name}"
                })
    return jsonify(videos)


# ── Controle do detector ──────────────────────────────────────────────────────

@app.route("/api/start", methods=["POST"])
def api_start():
    global detector, detector_thread
    if detector_thread and detector_thread.is_alive():
        return jsonify({"status": "already_running"}), 400

    data         = request.get_json() or {}
    source       = data.get("source", 0)
    preset_name  = data.get("preset", "general")
    camera_name  = data.get("camera_name", "Camera 1")

    from infracoes.detector import InfracaoDetector
    detector = InfracaoDetector(
        source          = source,
        preset_name     = preset_name,
        models_dir      = str(_BACKEND / "models"),
        output_dir      = str(_BACKEND / "outputs"),
        camera_name     = camera_name,
        show_window     = False,
        frame_queue     = frame_queue,
        infracoes_queue = infracoes_queue,
    )
    detector_thread = threading.Thread(target=detector.run, daemon=True)
    detector_thread.start()
    return jsonify({"status": "started"})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    if detector:
        detector.stop()
    return jsonify({"status": "stopped"})


# ── Standalone ────────────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(description="CogniMove Dashboard")
    p.add_argument("--source",  "-s", default=None)
    p.add_argument("--preset",  "-p", default="general")
    p.add_argument("--camera",  "-c", default="Camera 1")
    p.add_argument("--porta",   "-P", type=int, default=5000)
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.source is not None:
        from infracoes.detector import InfracaoDetector
        detector = InfracaoDetector(
            source          = args.source,
            preset_name     = args.preset,
            models_dir      = str(_BACKEND / "models"),
            output_dir      = str(_BACKEND / "outputs"),
            camera_name     = args.camera,
            show_window     = False,
            frame_queue     = frame_queue,
            infracoes_queue = infracoes_queue,
        )
        detector_thread = threading.Thread(target=detector.run, daemon=True)
        detector_thread.start()
        print(f"[Detector] Iniciado: {args.source}")

    print(f"[Dashboard] http://localhost:{args.porta}")
    app.run(host="0.0.0.0", port=args.porta,
            debug=False, use_reloader=False, threaded=True)
