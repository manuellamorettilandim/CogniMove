"""
Motor Central de Detecção de Infrações — CogniMove
Orquestra modelos YOLO, rastreador ByteTrack e todas as regras de infração.
"""
from __future__ import annotations
import os, sys, cv2, json, queue
import datetime
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Paths absolutos ───────────────────────────────────────────────────────────
_HERE    = Path(__file__).resolve().parent          # infracoes/
_DETECT  = _HERE.parent                             # detection/
_BACKEND = _DETECT.parent                           # backend/
_ROOT    = _BACKEND.parent                          # Cognimove_Melissa/

# Adicionar detection/ ao path para imports absolutos
sys.path.insert(0, str(_DETECT))

from ultralytics import YOLO
from infracoes.rastreador             import Rastreador, CLASSES_VEICULARES
from infracoes.regras.faixa_pedestre import RegraFaixaPedestre
from infracoes.regras.sinal_vermelho import RegraSinalVermelho
from infracoes.regras.bloqueio_cruzamento import RegraBloqueioCruzamento
from infracoes.evidencias            import GerenciadorEvidencias
from infracoes.relatorio             import GerenciadorRelatorio

# Módulos analíticos (Módulos 2 e 3 do artigo)
sys.path.insert(0, str(_BACKEND))
from analytics.contexto_urbano       import GerenciadorContextoUrbano
from analytics.causa_raiz            import MotorCausaRaiz

# Classes que o best.pt pode chamar de semáforo
_SEMAFORO_LABELS = {"semaforo", "semáforo", "traffic_light", "trafficlight"}


# ── Utilitários de preset ─────────────────────────────────────────────────────

def load_preset(name: str) -> dict:
    """Carrega JSON de backend/calibration/presets/<name>.json."""
    path = _ROOT / "backend" / "calibration" / "presets" / f"{name}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"name": name, "lines": [], "stop_lines": [],
            "polygons": [], "intersection_polygons": []}


def _scale_pt(pt, sx, sy):
    return [int(pt[0] * sx), int(pt[1] * sy)]


def scale_preset(preset: dict, width: int, height: int) -> dict:
    """Escala coordenadas do preset para a resolução atual."""
    rw = preset.get("ref_width",  width)
    rh = preset.get("ref_height", height)
    sx, sy = width / rw, height / rh

    def sl(line):
        return {**line, "pt1": _scale_pt(line["pt1"], sx, sy),
                        "pt2": _scale_pt(line["pt2"], sx, sy)}

    def sp(poly):
        return {**poly, "points": [_scale_pt(p, sx, sy) for p in poly["points"]]}

    return {
        **preset,
        "lines":                [sl(l) for l in preset.get("lines", [])],
        "stop_lines":           [sl(l) for l in preset.get("stop_lines", [])],
        "polygons":             [sp(p) for p in preset.get("polygons", [])],
        "intersection_polygons":[sp(p) for p in preset.get("intersection_polygons", [])],
    }


# ── Motor Central ─────────────────────────────────────────────────────────────

class InfracaoDetector:
    """Detecta infrações de trânsito em tempo real a partir de qualquer fonte de vídeo."""

    _LIGHT_COLORS = {
        "red": (0,0,255), "yellow": (0,165,255),
        "green": (0,220,0), "unknown": (110,110,110),
    }

    def __init__(self,
                 source,
                 preset_name:     str   = "general",
                 models_dir:      str   = None,
                 output_dir:      str   = None,
                 camera_name:     str   = "camera",
                 show_window:     bool  = False,
                 frame_queue:     queue.Queue | None = None,
                 infracoes_queue: queue.Queue | None = None,
                 contexto_urbano: GerenciadorContextoUrbano | None = None,
                 motor_causa_raiz: MotorCausaRaiz | None = None):
        """
        Args:
            source:          0 (webcam), "rtsp://...", ou caminho de arquivo .mp4
            preset_name:     Nome do arquivo JSON em calibration/presets/
            models_dir:      Pasta com best.pt e yolov8n.pt
            output_dir:      Pasta raiz para evidências e relatórios
            camera_name:     Identificador da câmera no relatório
            show_window:     Exibir janela OpenCV durante processamento
            frame_queue:     Queue para streaming de frames ao Flask
            infracoes_queue: Queue para notificações SSE ao Flask
        """
        self.source          = source
        self.preset_name     = preset_name
        self.camera_name     = camera_name
        self.show_window     = show_window
        self.frame_queue     = frame_queue
        self.infracoes_queue = infracoes_queue
        self._running        = False
        self.frame_idx       = 0

        # Módulos analíticos (Módulos 2 e 3)
        if contexto_urbano is None:
            logger.warning(
                "InfracaoDetector(%s) instanciado sem contexto_urbano compartilhado — "
                "usando instância isolada; alterações feitas no dashboard não serão "
                "refletidas neste detector.",
                camera_name,
            )
            contexto_urbano = GerenciadorContextoUrbano()
        self.contexto_urbano = contexto_urbano

        if motor_causa_raiz is None:
            logger.warning(
                "InfracaoDetector(%s) instanciado sem motor_causa_raiz compartilhado — "
                "usando instância isolada.",
                camera_name,
            )
            motor_causa_raiz = MotorCausaRaiz()
        self.motor_causa_raiz = motor_causa_raiz

        self.models_dir = models_dir or str(_BACKEND / "models")
        self.output_dir = output_dir or str(_BACKEND / "outputs")

        # Módulos (inicializados em _setup após abrir a fonte)
        self.rastreador:   Rastreador           | None = None
        self.model_limite: YOLO                 | None = None
        self.regra_faixa:  RegraFaixaPedestre   | None = None
        self.regra_sinal:  RegraSinalVermelho   | None = None
        self.regra_bloq:   RegraBloqueioCruzamento | None = None
        self.evidencias:   GerenciadorEvidencias  | None = None
        self.relatorio:    GerenciadorRelatorio   | None = None
        self._preset:      dict                  | None = None

        self.stats = {
            "total": 0,
            "AVANCO_SINAL_VERMELHO": 0,
            "INVASAO_FAIXA": 0,
            "BLOQUEIO_CRUZAMENTO": 0,
        }

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _setup(self, width: int, height: int, fps: float):
        """Instancia todos os módulos com a resolução real da fonte."""
        raw = load_preset(self.preset_name)
        self._preset = scale_preset(raw, width, height)

        # Linha de retenção padrão se preset não tem nenhuma
        if not self._preset["lines"] and not self._preset["stop_lines"]:
            default = {"name": "Linha de Retencao",
                       "pt1": [int(width*0.05), int(height*0.72)],
                       "pt2": [int(width*0.95), int(height*0.72)],
                       "color": [0,255,255]}
            self._preset["lines"]      = [default]
            self._preset["stop_lines"] = [default]

        # Modelos
        best_pt   = os.path.join(self.models_dir, "best.pt")
        yolo_pt   = os.path.join(self.models_dir, "yolov8n.pt")
        track_mdl = yolo_pt if os.path.exists(yolo_pt) else "yolov8n.pt"

        self.rastreador   = Rastreador(track_mdl)
        self.model_limite = YOLO(best_pt) if os.path.exists(best_pt) else None
        if not self.model_limite:
            print("[Aviso] best.pt não encontrado — detecção de semáforo desativada.")

        # Regras
        lines  = self._preset.get("lines", [])
        stops  = self._preset.get("stop_lines", lines)
        polys  = self._preset.get("polygons", [])
        inters = self._preset.get("intersection_polygons", [])

        self.regra_faixa = RegraFaixaPedestre(lines=lines, polygons=polys)
        self.regra_sinal = RegraSinalVermelho(stop_lines=stops)
        self.regra_bloq  = RegraBloqueioCruzamento(intersection_polygons=inters, fps=fps)

        # Evidências e relatório
        ev_dir  = os.path.join(self.output_dir, "evidencias")
        rel_dir = os.path.join(self.output_dir, "relatorios")
        self.evidencias = GerenciadorEvidencias(ev_dir, fps=fps)
        self.relatorio  = GerenciadorRelatorio(rel_dir, camera_name=self.camera_name)

        print(f"[Detector] {width}x{height} @ {fps:.1f}fps | preset={self.preset_name}")
        print(f"[Detector] {len(lines)} linhas | {len(polys)} polígonos | "
              f"{len(inters)} zonas de cruzamento")

    # ── Processamento por frame ───────────────────────────────────────────────

    def _process_frame(self, frame):
        self.frame_idx += 1

        # 1. Rastreamento de veículos e pedestres
        tracks = self.rastreador.update(frame)

        # Filtrar apenas veículos para as regras de infração (pedestres continuam em tracks para exibição)
        tracks_veiculos = [t for t in tracks if t.cls_id in CLASSES_VEICULARES]

        # 2. Detectar semáforos
        detected_lights: list[dict] = []
        if self.model_limite:
            res = self.model_limite.predict(frame, conf=0.20, verbose=False)
            if res and res[0].boxes:
                for box in res[0].boxes:
                    lbl = self.model_limite.names.get(int(box.cls[0]), "").lower()
                    if any(k in lbl for k in _SEMAFORO_LABELS):
                        x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())
                        detected_lights.append({"bbox": (x1,y1,x2,y2)})

        light_state = self.regra_sinal.get_light_state()

        # 3. Aplicar regras (apenas para classes veiculares)
        infractions: list[dict] = []
        infractions += self.regra_faixa.checar(frame, tracks_veiculos, light_state, self.frame_idx)
        infractions += self.regra_sinal.checar(frame, tracks_veiculos, detected_lights, self.frame_idx)
        infractions += self.regra_bloq.checar(frame, tracks_veiculos, light_state, self.frame_idx)

        # 4. Registrar evidências e relatório (com causa-raiz)
        for inf in infractions:
            ev = self.evidencias.registrar(inf, frame)

            # Módulo 2+3: obter contexto e calcular causa-raiz
            contexto = self.contexto_urbano.obter_contexto_atual()
            analise  = self.motor_causa_raiz.calcular_probabilidades(
                inf["tipo"], contexto
            )

            self.relatorio.adicionar(inf, ev, analise_causa=analise)
            self.stats["total"] += 1
            self.stats[inf["tipo"]] = self.stats.get(inf["tipo"], 0) + 1
            if self.infracoes_queue is not None:
                try:
                    self.infracoes_queue.put_nowait(inf)
                except queue.Full:
                    pass

        # 5. Anotar frame
        annotated = self._draw(frame.copy(), tracks, detected_lights, infractions)

        # 6. Alimentar buffer de evidências com frame anotado
        self.evidencias.push_frame(annotated)

        return annotated, infractions

    # ── Desenho ───────────────────────────────────────────────────────────────

    def _draw(self, frame, tracks, detected_lights, infractions):
        """Aplica todas as camadas de anotação visual."""
        self.regra_faixa.draw(frame, infractions)
        self.regra_sinal.draw(frame, detected_lights)
        self.regra_bloq.draw(frame, tracks, self.frame_idx)

        inf_ids = {i["track_id"] for i in infractions}
        for t in tracks:
            if not t.active or not t.current:
                continue
            x1,y1,x2,y2 = t.current["bbox"]
            is_inf = t.id in inf_ids
            color  = (0,0,255) if is_inf else (0,200,60)
            cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)

            if is_inf:
                inf = next(i for i in infractions if i["track_id"]==t.id)
                label = f"! {inf['tipo'].replace('_',' ')} #{t.id}"
            else:
                label = f"{t.cls_name} #{t.id}"

            (tw,th),_ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.44, 1)
            cv2.rectangle(frame,(x1,y1-th-6),(x1+tw+4,y1),color,-1)
            cv2.putText(frame, label,(x1+2,y1-3),
                        cv2.FONT_HERSHEY_SIMPLEX,0.44,(255,255,255),1,cv2.LINE_AA)

        self._draw_hud(frame)
        return frame

    def _draw_hud(self, frame):
        h, w = frame.shape[:2]
        light = self.regra_sinal.get_light_state() if self.regra_sinal else "unknown"
        lc    = self._LIGHT_COLORS.get(light, (110,110,110))

        cv2.rectangle(frame,(0,0),(w,78),(12,12,12),-1)
        cv2.line(frame,(0,78),(w,78),lc,2)

        cv2.putText(frame,"COGNIMOVE  |  MONITORAMENTO DE INFRACOES EM TEMPO REAL",
                    (10,24),cv2.FONT_HERSHEY_SIMPLEX,0.52,(0,220,220),1,cv2.LINE_AA)
        cv2.putText(frame,
                    f"Camara: {self.camera_name}   Frame: {self.frame_idx}   "
                    f"Semaforo: {light.upper()}   "
                    f"{datetime.datetime.now().strftime('%H:%M:%S')}",
                    (10,46),cv2.FONT_HERSHEY_SIMPLEX,0.40,(190,190,190),1,cv2.LINE_AA)

        stat_txt = (f"Total: {self.stats['total']}   "
                    f"Sinal Verm.: {self.stats.get('AVANCO_SINAL_VERMELHO',0)}   "
                    f"Faixa: {self.stats.get('INVASAO_FAIXA',0)}   "
                    f"Bloqueio: {self.stats.get('BLOQUEIO_CRUZAMENTO',0)}")
        cv2.putText(frame,stat_txt,(10,66),cv2.FONT_HERSHEY_SIMPLEX,0.40,lc,1,cv2.LINE_AA)

        # Círculo indicador de semáforo
        cx,cy,r = w-32,32,20
        cv2.circle(frame,(cx,cy),r+2,(30,30,30),-1)
        cv2.circle(frame,(cx,cy),r,lc,-1)
        cv2.circle(frame,(cx,cy),r,(200,200,200),1)

    # ── Loop principal ────────────────────────────────────────────────────────

    def run(self):
        """Inicia o loop de detecção. Bloqueia até encerrar."""
        self._running = True

        src = self.source
        if isinstance(src, str):
            src_str = src.strip()
            if src_str.isdigit():
                src = int(src_str)
            elif not src_str.startswith(("rtsp://", "http://", "https://")):
                p = Path(src_str)
                if p.is_absolute() and p.exists():
                    src = str(p)
                elif (_ROOT / p).exists():
                    src = str(_ROOT / p)
                elif (_ROOT / "videos_teste" / p.name).exists():
                    src = str(_ROOT / "videos_teste" / p.name)
        elif isinstance(src, (int, float)):
            src = int(src)

        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            print(f"[Erro] Não foi possível abrir: {self.source} (resolvido como: {src})")
            return

        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0

        self._setup(width, height, fps)
        print(f"[Detector] Monitorando: {self.source}  (Q para sair)")

        while self._running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("[Detector] Fim da fonte de vídeo.")
                break

            annotated, _ = self._process_frame(frame)

            # Enviar frame JPEG para streaming Flask
            if self.frame_queue is not None:
                ok, buf = cv2.imencode(".jpg", annotated,
                                       [cv2.IMWRITE_JPEG_QUALITY, 72])
                if ok:
                    bts = buf.tobytes()
                    try:
                        self.frame_queue.put_nowait(bts)
                    except queue.Full:
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put_nowait(bts)
                        except Exception:
                            pass

            if self.show_window:
                cv2.imshow("CogniMove — Infracoes", annotated)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break

        cap.release()
        if self.show_window:
            cv2.destroyAllWindows()

        total = self.stats["total"]
        print(f"\n[Detector] Encerrado. {total} infração(ões) detectada(s).")
        if self.relatorio:
            print(f"[Detector] Relatório: {self.relatorio.csv_path}")

    def stop(self):
        self._running = False
