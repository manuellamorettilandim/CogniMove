"""
Regra: Avanço de Sinal Vermelho
Classifica o estado do semáforo por análise HSV e detecta cruzamento
da linha de retenção enquanto o sinal está vermelho.
"""
from __future__ import annotations
import cv2
import datetime
import numpy as np
from collections import deque


# ── Classificador HSV ─────────────────────────────────────────────────────────

def classify_traffic_light_hsv(frame, bbox: tuple) -> str:
    """
    Classifica o estado do semáforo (red / yellow / green / unknown) por
    análise HSV nas três regiões horizontais do bounding box.

    Divide o bbox em terços verticais:
      - superior  → lâmpada vermelha
      - central   → lâmpada amarela
      - inferior  → lâmpada verde
    """
    x1, y1, x2, y2 = bbox
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(frame.shape[1], x2); y2 = min(frame.shape[0], y2)

    h = y2 - y1
    w = x2 - x1
    if h < 10 or w < 4:
        return "unknown"

    h3 = h // 3
    top_roi    = frame[y1        : y1 + h3,      x1:x2]
    mid_roi    = frame[y1 + h3   : y1 + 2*h3,    x1:x2]
    bottom_roi = frame[y1 + 2*h3 : y2,            x1:x2]

    def count_hsv(roi, ranges):
        if roi.size == 0:
            return 0
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        total = 0
        for lo, hi in ranges:
            total += cv2.countNonZero(cv2.inRange(hsv, np.array(lo), np.array(hi)))
        return total

    # Vermelho: dois intervalos (H wraps around 0/180)
    red    = count_hsv(top_roi,    [([0,120,80],[10,255,255]), ([170,120,80],[180,255,255])])
    yellow = count_hsv(mid_roi,    [([18,120,80],[38,255,255])])
    green  = count_hsv(bottom_roi, [([40,100,80],[80,255,255])])

    best = max(red, yellow, green)
    if best < 8:
        return "unknown"
    if best == red:
        return "red"
    if best == yellow:
        return "yellow"
    return "green"


# ── Geometria ─────────────────────────────────────────────────────────────────

def _ccw(A, B, C):
    return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])


def segments_intersect(p1, p2, p3, p4) -> bool:
    return (_ccw(p1,p3,p4) != _ccw(p2,p3,p4)) and (_ccw(p1,p2,p3) != _ccw(p1,p2,p4))


# ── Regra principal ───────────────────────────────────────────────────────────

class RegraSinalVermelho:
    """Detecta avanço de sinal vermelho com suavização do estado do semáforo."""

    STATE_COLORS = {
        "red":     (0,   0, 255),
        "yellow":  (0, 165, 255),
        "green":   (0, 200,   0),
        "unknown": (128,128,128),
    }

    def __init__(self,
                 stop_lines: list,
                 smoothing_frames: int = 5,
                 cooldown_frames:  int = 60):
        """
        Args:
            stop_lines:       Linhas de retenção {name, pt1, pt2}
            smoothing_frames: Janela de suavização (evita falsos por frame único)
            cooldown_frames:  Cooldown por veículo entre alertas
        """
        self.stop_lines      = stop_lines or []
        self.smoothing_frames = smoothing_frames
        self.cooldown_frames  = cooldown_frames
        self._state_buffer: deque = deque(maxlen=smoothing_frames)
        self._current_state  = "unknown"
        self._cooldown: dict[int, int] = {}

    # ── Estado ────────────────────────────────────────────────────────────────

    def get_light_state(self) -> str:
        return self._current_state

    def _smooth_state(self, raw: str) -> str:
        self._state_buffer.append(raw)
        counts: dict[str, int] = {}
        for s in self._state_buffer:
            if s != "unknown":
                counts[s] = counts.get(s, 0) + 1
        return max(counts, key=counts.get) if counts else "unknown"

    # ── Checagem ──────────────────────────────────────────────────────────────

    def checar(self, frame, tracks: list,
               detected_lights: list[dict], frame_idx: int) -> list[dict]:
        """
        Args:
            detected_lights: [{'bbox': (x1,y1,x2,y2)}, ...] do model_limite
        """
        # Classificar estado do semáforo neste frame
        raw = "unknown"
        for light in detected_lights:
            s = classify_traffic_light_hsv(frame, light["bbox"])
            if s != "unknown":
                raw = s
                break
        self._current_state = self._smooth_state(raw)

        infractions = []
        if self._current_state != "red":
            return infractions

        for track in tracks:
            if not track.active or track.previous is None:
                continue
            if track.id in self._cooldown:
                if frame_idx - self._cooldown[track.id] < self.cooldown_frames:
                    continue

            p1 = track.previous["bottom_pt"]
            p2 = track.current["bottom_pt"]

            for line in self.stop_lines:
                if segments_intersect(p1, p2, tuple(line["pt1"]), tuple(line["pt2"])):
                    self._cooldown[track.id] = frame_idx
                    infractions.append({
                        "tipo":             "AVANCO_SINAL_VERMELHO",
                        "descricao":        f"Cruzou {line.get('name','linha de retenção')} com sinal VERMELHO",
                        "track_id":         track.id,
                        "classe":           track.cls_name,
                        "bbox":             track.current["bbox"],
                        "frame":            frame_idx,
                        "timestamp":        datetime.datetime.now().isoformat(),
                        "confianca":        round(track.current.get("conf", 0.0), 3),
                        "estado_semaforo":  self._current_state,
                    })
                    break

        return infractions

    # ── Desenho ──────────────────────────────────────────────────────────────

    def draw(self, frame, detected_lights: list[dict]):
        color = self.STATE_COLORS.get(self._current_state, (128,128,128))

        # Bounding boxes dos semáforos
        for light in detected_lights:
            x1, y1, x2, y2 = light["bbox"]
            cv2.rectangle(frame, (x1,y1),(x2,y2), color, 2)
            label = f"SEMAFORO [{self._current_state.upper()}]"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            cv2.rectangle(frame, (x1, y1-th-6), (x1+tw+4, y1), color, -1)
            cv2.putText(frame, label, (x1+2, y1-3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0,0,0), 1, cv2.LINE_AA)

        # Linhas de retenção
        for line in self.stop_lines:
            pt1 = tuple(line["pt1"])
            pt2 = tuple(line["pt2"])
            cv2.line(frame, pt1, pt2, (0,0,0), 5)
            cv2.line(frame, pt1, pt2, color, 3)
            mid = ((pt1[0]+pt2[0])//2, (pt1[1]+pt2[1])//2 - 8)
            label = f"[ RETENCAO • {self._current_state.upper()} ]"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
            cv2.rectangle(frame, (mid[0]-2, mid[1]-th-4), (mid[0]+tw+2, mid[1]+2), (0,0,0), -1)
            cv2.putText(frame, label, mid, cv2.FONT_HERSHEY_SIMPLEX, 0.40, color, 1, cv2.LINE_AA)

        return frame
