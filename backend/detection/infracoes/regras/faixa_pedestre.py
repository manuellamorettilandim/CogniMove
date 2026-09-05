"""
Regra: Invasão de Faixa de Pedestres / Bike Box
Detecta cruzamento de linhas de limite e invasão de polígonos protegidos.
"""
from __future__ import annotations
import cv2
import datetime
import numpy as np


# ── Funções geométricas ───────────────────────────────────────────────────────

def _ccw(A, B, C):
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])


def segments_intersect(p1, p2, p3, p4) -> bool:
    """Retorna True se o segmento p1→p2 intersecta p3→p4."""
    return (
        _ccw(p1, p3, p4) != _ccw(p2, p3, p4) and
        _ccw(p1, p2, p3) != _ccw(p1, p2, p4)
    )


def point_in_polygon(pt, polygon_pts) -> bool:
    """Retorna True se pt está dentro do polígono (ray casting via OpenCV)."""
    if not polygon_pts or len(polygon_pts) < 3:
        return False
    poly = np.array(polygon_pts, np.int32).reshape(-1, 1, 2)
    return cv2.pointPolygonTest(poly, (float(pt[0]), float(pt[1])), False) >= 0


# ── Regra principal ───────────────────────────────────────────────────────────

class RegraFaixaPedestre:
    """Detecta invasão de faixa de pedestres e/ou bike box."""

    def __init__(self, lines: list, polygons: list = None, cooldown_frames: int = 30):
        """
        Args:
            lines:           Lista de dicts {name, pt1, pt2, color}
            polygons:        Lista de dicts {name, points}
            cooldown_frames: Frames de espera antes de re-alertar o mesmo veículo
        """
        self.lines    = lines or []
        self.polygons = polygons or []
        self.cooldown_frames = cooldown_frames
        self._cooldown: dict[int, int] = {}

    def checar(self, frame, tracks: list, light_state: str, frame_idx: int) -> list[dict]:
        """Verifica infrações de invasão de faixa nos tracks ativos."""
        infractions = []
        for track in tracks:
            if not track.active or track.current is None:
                continue
            if track.id in self._cooldown:
                if frame_idx - self._cooldown[track.id] < self.cooldown_frames:
                    continue

            desc = (
                self._check_line_crossing(track) or
                self._check_polygon_invasion(track.current["bottom_pt"])
            )
            if desc:
                self._cooldown[track.id] = frame_idx
                infractions.append({
                    "tipo":      "INVASAO_FAIXA",
                    "descricao": desc,
                    "track_id":  track.id,
                    "classe":    track.cls_name,
                    "bbox":      track.current["bbox"],
                    "frame":     frame_idx,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "confianca": round(track.current.get("conf", 0.0), 3),
                })
        return infractions

    def _check_line_crossing(self, track) -> str | None:
        if track.previous is None:
            return None
        p1 = track.previous["bottom_pt"]
        p2 = track.current["bottom_pt"]
        for line in self.lines:
            if segments_intersect(p1, p2, tuple(line["pt1"]), tuple(line["pt2"])):
                return f"Cruzou {line.get('name', 'linha de limite')}"
        return None

    def _check_polygon_invasion(self, bottom_pt) -> str | None:
        for poly in self.polygons:
            if point_in_polygon(bottom_pt, poly.get("points", [])):
                return f"Invasão de {poly.get('name', 'área protegida')}"
        return None

    # ── Desenho ──────────────────────────────────────────────────────────────

    def draw(self, frame, infractions_frame: list[dict]):
        """Desenha zonas, linhas e alertas visuais no frame."""
        overlay = frame.copy()
        for poly in self.polygons:
            pts = np.array(poly.get("points", []), np.int32)
            if len(pts) >= 3:
                cv2.fillPoly(overlay, [pts], (255, 200, 0))
        cv2.addWeighted(overlay, 0.20, frame, 0.80, 0, frame)

        for line in self.lines:
            pt1   = tuple(line["pt1"])
            pt2   = tuple(line["pt2"])
            color = tuple(line.get("color", [0, 255, 255]))
            name  = line.get("name", "Limite")
            cv2.line(frame, pt1, pt2, (0, 0, 0), 5)
            cv2.line(frame, pt1, pt2, color, 3)
            mid = ((pt1[0] + pt2[0]) // 2, (pt1[1] + pt2[1]) // 2 - 8)
            label = f"[ {name} ]"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (mid[0]-4, mid[1]-th-4), (mid[0]+tw+4, mid[1]+4), (0,0,0), -1)
            cv2.putText(frame, label, mid, cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

        for poly in self.polygons:
            pts = np.array(poly.get("points", []), np.int32)
            if len(pts) >= 3:
                cv2.polylines(frame, [pts.reshape(-1,1,2)], True, (255,200,0), 2)
        return frame
