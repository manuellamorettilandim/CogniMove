"""
CogniMove — Dashboard Web (Flask)
Streaming MJPEG + SSE para infrações em tempo real.

Uso standalone:
  python app.py --source 0 --preset caetano_alvares

Uso via monitorar_infracoes.py:
  python ../backend/detection/monitorar_infracoes.py --source 0 --dashboard
"""
from __future__ import annotations
import os, sys, json, queue, threading, argparse, datetime
from pathlib import Path
from flask import (Flask, render_template, Response, jsonify,
                   request, stream_with_context, send_from_directory)

_FRONTEND = Path(__file__).resolve().parent
_ROOT     = _FRONTEND.parent
_BACKEND  = _ROOT / "backend"
_DETECT   = _BACKEND / "detection"

sys.path.insert(0, str(_DETECT))
sys.path.insert(0, str(_ROOT))

app = Flask(__name__, template_folder="templates", static_folder="static")

# ── Estado compartilhado (injetado por monitorar_infracoes.py ou criado aqui) ─
frame_queue:     queue.Queue = queue.Queue(maxsize=2)
infracoes_queue: queue.Queue = queue.Queue(maxsize=500)
detector = None
detector_thread: threading.Thread | None = None

# ── Estado do Simulador de Câmera (Área 3 — ponte via arquivo de relatório) ──
TIPOS_INFRACAO_VALIDOS = {
    "AVANCO_SINAL_VERMELHO",
    "INVASAO_FAIXA",
    "BLOQUEIO_CRUZAMENTO",
}
_simulador_lock = threading.Lock()
_simulador_estado = {
    "contexto": None,
    "motor": None,
    "relatorio": None,
}


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
    """Retorna lista de vídeos disponíveis em videos_teste/ e videos_originais/."""
    videos = []
    for pasta_nome in ("videos_teste", "videos_originais"):
        pasta = _ROOT / pasta_nome
        if pasta.exists():
            for f in sorted(pasta.iterdir()):
                if f.is_file() and f.suffix.lower() in ('.mp4', '.avi', '.mkv', '.mov'):
                    videos.append({
                        "filename": f.name,
                        "path": f"{pasta_nome}/{f.name}"
                    })
    return jsonify(videos)


# ── Simulador de Câmera (Área 3 do dashboard Streamlit lê o mesmo relatório) ──

@app.route("/simulador")
def simulador_configuracao():
    """Tela de configuração do simulador: data, hora e obra viária."""
    return render_template("simulador.html")


@app.route("/simulador/camera")
def simulador_camera():
    """Tela da câmera simulada (Canvas/JS)."""
    return render_template("simulador_camera.html")


@app.route("/api/simulador/iniciar", methods=["POST"])
def api_simulador_iniciar():
    """Consulta o contexto urbano real para a data/hora escolhida e inicia a sessão."""
    from backend.analytics.causa_raiz import MotorCausaRaiz
    from backend.analytics.contexto_tempo_real import construir_contexto_a_partir_de_data
    from infracoes.relatorio import GerenciadorRelatorio

    dados = request.get_json() or {}
    data_str  = dados.get("data")
    hora_str  = dados.get("hora")
    obra_viaria = bool(dados.get("obra_viaria", False))

    if not data_str or not hora_str:
        return jsonify({"erro": "Campos 'data' e 'hora' são obrigatórios."}), 400

    try:
        data = datetime.date.fromisoformat(data_str)
        hora = datetime.time.fromisoformat(hora_str)
    except ValueError:
        return jsonify({"erro": "Formato inválido para 'data' (AAAA-MM-DD) ou 'hora' (HH:MM)."}), 400

    contexto = construir_contexto_a_partir_de_data(data, hora, obra_viaria_manual=obra_viaria)

    with _simulador_lock:
        _simulador_estado["contexto"]  = contexto
        _simulador_estado["motor"]     = MotorCausaRaiz()
        _simulador_estado["relatorio"] = GerenciadorRelatorio(
            str(_BACKEND / "outputs" / "relatorios"),
            camera_name="Simulador",
        )

    return jsonify(contexto)


@app.route("/api/simulador/infracao", methods=["POST"])
def api_simulador_infracao():
    """Registra uma infração marcada manualmente na câmera simulada."""
    dados = request.get_json() or {}
    tipo = dados.get("tipo")

    if tipo not in TIPOS_INFRACAO_VALIDOS:
        return jsonify({"erro": f"Tipo de infração inválido: {tipo!r}."}), 400

    with _simulador_lock:
        contexto  = _simulador_estado["contexto"]
        motor     = _simulador_estado["motor"]
        relatorio = _simulador_estado["relatorio"]

    if contexto is None or motor is None or relatorio is None:
        return jsonify({"erro": "Simulação não iniciada. Chame /api/simulador/iniciar primeiro."}), 400

    analise = motor.calcular_probabilidades(tipo, contexto)

    infracao = {
        "timestamp": datetime.datetime.now().isoformat(),
        "tipo": tipo,
        "descricao": tipo.replace("_", " ").title(),
        "track_id": -1,
        "classe": "carro",
        "confianca": 1.0,
    }
    relatorio.adicionar(infracao, evidencias={}, analise_causa=analise)

    return jsonify(analise)


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
