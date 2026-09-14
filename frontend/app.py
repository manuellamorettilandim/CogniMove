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


# ── Controle do detector ──────────────────────────────────────────────────────

@app.route("/api/start", methods=["POST"])
def api_start():
    global detector, detector_thread
    # Safety: ensure any previous detector thread is stopped before starting a new one
    if detector_thread and detector_thread.is_alive():
        if detector:
            detector.stop()
        detector_thread.join(timeout=3.0)
    if detector_thread and detector_thread.is_alive():
        return jsonify({"status": "already_running"}), 400

    # Clear any residual frames/infractions from previous run
    while not frame_queue.empty():
        try:
            frame_queue.get_nowait()
        except queue.Empty:
            break
    while not infracoes_queue.empty():
        try:
            infracoes_queue.get_nowait()
        except queue.Empty:
            break

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
        desenhar_hud_completo = False,
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
    if detector_thread and detector_thread.is_alive():
        detector_thread.join(timeout=3.0)
    return jsonify({"status": "stopped"})


# ── Standalone ────────────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(description="CogniMove Dashboard")
    p.add_argument("--source",  "-s", default=None)
    p.add_argument("--preset",  "-p", default="general")
    p.add_argument("--camera",  "-c", default="Camera 1")
    p.add_argument("--porta",   "-P", type=int, default=5000)
    return p.parse_args()


# ═══════════════════════════════════════════════════════════════════════════
# NOVOS ENDPOINTS — Site de Demonstração FECART
# ═══════════════════════════════════════════════════════════════════════════

# ── Analytics: Contexto Urbano + Causa-Raiz ───────────────────────────────
# O __init__.py de backend/analytics/ usa `from backend.analytics.X import Y`,
# o que exige que _ROOT (raiz do projeto) esteja no sys.path.
# Importamos os módulos DIRETAMENTE (sem passar pelo __init__) para evitar
# acionar o import absoluto que depende de 'backend' como pacote de topo.

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import importlib.util as _ilu

    def _load_module(name, path):
        spec = _ilu.spec_from_file_location(name, path)
        mod  = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    _mod_ctx  = _load_module("contexto_urbano", str(_BACKEND / "analytics" / "contexto_urbano.py"))
    _mod_causa = _load_module("causa_raiz",      str(_BACKEND / "analytics" / "causa_raiz.py"))

    GerenciadorContextoUrbano = _mod_ctx.GerenciadorContextoUrbano
    MotorCausaRaiz            = _mod_causa.MotorCausaRaiz

    _contexto_urbano: "GerenciadorContextoUrbano | None" = GerenciadorContextoUrbano()
    _motor_causa_raiz: "MotorCausaRaiz | None"           = MotorCausaRaiz()
    print("[Analytics] ContextoUrbano + MotorCausaRaiz carregados.")
except Exception as _analytics_err:
    _contexto_urbano  = None
    _motor_causa_raiz = None
    print(f"[Aviso] Analytics não carregados: {_analytics_err}")


@app.route("/api/contexto", methods=["GET", "POST"])
def api_contexto():
    """GET: retorna contexto urbano atual. POST: {flag, estado} para ativar/desativar cenário."""
    if _contexto_urbano is None:
        return jsonify({"error": "Analytics não disponível"}), 503
    if request.method == "POST":
        data  = request.get_json() or {}
        flag  = data.get("flag", "")
        estado = bool(data.get("estado", False))
        try:
            _contexto_urbano.set_flag(flag, estado)
        except KeyError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"ok": True, "contexto": _contexto_urbano.obter_contexto_atual()})
    return jsonify(_contexto_urbano.obter_contexto_atual())


@app.route("/api/causa_raiz")
def api_causa_raiz():
    """Calcula causa-raiz probabilística. Query params: tipo=<CODIGO>, contexto opcional."""
    if _motor_causa_raiz is None or _contexto_urbano is None:
        return jsonify({"error": "Analytics não disponível"}), 503
    tipo = request.args.get("tipo", "")
    ctx  = _contexto_urbano.obter_contexto_atual()
    resultado = _motor_causa_raiz.calcular_probabilidades(tipo, ctx)
    return jsonify(resultado)


# ── Curados ───────────────────────────────────────────────────────────────

_CURADOS_REAL = _BACKEND / "outputs" / "curados" / "real"
_CURADOS_GTA  = _BACKEND / "outputs" / "curados" / "gta"


def _listar_curados(pasta: Path) -> list:
    """Lê todos os .json de uma pasta de curados, retorna lista de dicts."""
    if not pasta.exists():
        return []
    registros = []
    for jf in sorted(pasta.glob("*.json")):
        try:
            with open(jf, encoding="utf-8") as fh:
                rec = json.load(fh)
            rec.setdefault("_arquivo", jf.name)
            registros.append(rec)
        except Exception:
            pass
    return registros


@app.route("/api/curados")
def api_curados():
    """Ocorrências curadas de vídeo real (Monitoramento/Análise)."""
    return jsonify(_listar_curados(_CURADOS_REAL))


@app.route("/api/curados/gta")
def api_curados_gta():
    """Ocorrências curadas dos vídeos GTA (Interatividade)."""
    return jsonify(_listar_curados(_CURADOS_GTA))


@app.route("/clips/<path:filename>")
@app.route("/static/clips/<path:filename>")
def servir_clip(filename):
    """
    Serve MP4/JPG de clipes curados com suporte a HTTP Range requests.

    Flask ≥ 2.x: send_from_directory chama send_file com conditional=True (padrão),
    ativando ETag, Last-Modified e suporte a Range (HTTP 206 Partial Content).
    O Werkzeug intercepta o header Range: bytes=X-Y do browser e retorna apenas
    o trecho solicitado — necessário para play/seek no <video> sem baixar o arquivo
    inteiro. conditional=True é passado explicitamente para deixar o comportamento
    documentado e garantido independente de versão do Flask.
    """
    for pasta in (_CURADOS_REAL, _CURADOS_GTA, _BACKEND / "outputs"):
        alvo = pasta / filename
        if alvo.exists() and alvo.is_file():
            return send_from_directory(str(pasta), filename, conditional=True)
    return "Clipe não encontrado", 404


# ── Relatório Histórico ───────────────────────────────────────────────────

@app.route("/api/relatorio/historico")
def api_relatorio_historico():
    """
    Consolida registros de sessões passadas (todos os .jsonl em backend/outputs/)
    mais a sessão corrente em memória (se detector estiver ativo).
    O .jsonl da sessão atual é excluído da leitura de disco para evitar duplicatas —
    seus dados vêm diretamente do get_records() em memória.
    """
    outputs_dir = _BACKEND / "outputs"
    sessao_jsonl = (
        Path(detector.relatorio.jsonl_path).resolve()
        if detector and detector.relatorio
        else None
    )

    passados: list[dict] = []
    if outputs_dir.exists():
        for jf in sorted(outputs_dir.glob("**/*.jsonl")):
            if sessao_jsonl and jf.resolve() == sessao_jsonl:
                continue  # Sessão atual virá da memória
            try:
                with open(jf, encoding="utf-8") as fh:
                    for linha in fh:
                        linha = linha.strip()
                        if linha:
                            try:
                                passados.append(json.loads(linha))
                            except json.JSONDecodeError:
                                pass
            except Exception:
                pass

    correntes: list[dict] = (
        detector.relatorio.get_records() if detector and detector.relatorio else []
    )
    return jsonify(passados + correntes)


# ═══════════════════════════════════════════════════════════════════════════

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
