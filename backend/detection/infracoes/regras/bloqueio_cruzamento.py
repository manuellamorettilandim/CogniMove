"""
Regra: Bloqueio de Cruzamento
Detecta veículos parados dentro da área do cruzamento por mais de N segundos.
"""
from __future__ import annotations
import cv2
import datetime
import numpy as np


def _point_in_polygon(pt, polygon_pts) -> bool:
    if not polygon_pts or len(polygon_pts) < 3:
        return False
    poly = np.array(polygon_pts, np.int32).reshape(-1, 1, 2)
    return cv2.pointPolygonTest(poly, (float(pt[0]), float(pt[1])), False) >= 0


class RegraBloqueioCruzamento:
    """Detecta bloqueio de cruzamento (veículo parado na área por > threshold_seconds)."""

    def __init__(self,
                 intersection_polygons: list,
                 fps: float = 30.0,
                 threshold_seconds: float = 5.0,
                 cooldown_seconds:  float = 10.0):
        """
        Args:
            intersection_polygons: [{name, points}, ...]
            fps:                   FPS da fonte de vídeo
            threshold_seconds:     Tempo mínimo dentro do cruzamento para alertar
            cooldown_seconds:      Cooldown entre alertas para o mesmo veículo
        """
        self.polygons          = intersection_polygons or []
        self.fps               = max(fps, 1.0)
        self.threshold_frames  = int(threshold_seconds * fps)
        self.cooldown_frames   = int(cooldown_seconds  * fps)
        self._inside_since: dict[int, int]  = {}  # track_id → primeiro frame dentro
        self._cooldown: dict[int, int]       = {}  # track_id → último frame alertado

    def checar(self, frame, tracks: list, light_state: str, frame_idx: int) -> list[dict]:
        infractions = []
        active_ids = {t.id for t in tracks if t.active}

        # Remover tracks inativos do histórico interno
        for tid in list(self._inside_since.keys()):
            if tid not in active_ids:
                del self._inside_since[tid]

        for track in tracks:
            if not track.active or track.current is None:
                continue

            centroid = track.current["centroid"]
            in_zone  = any(
                _point_in_polygon(centroid, poly.get("points", []))
                for poly in self.polygons
            )

            if in_zone:
                if track.id not in self._inside_since:
                    self._inside_since[track.id] = frame_idx

                frames_inside = frame_idx - self._inside_since[track.id]

                if frames_inside >= self.threshold_frames:
                    if track.id in self._cooldown:
                        if frame_idx - self._cooldown[track.id] < self.cooldown_frames:
                            continue
                    secs = frames_inside / self.fps
                    self._cooldown[track.id] = frame_idx
                    infractions.append({
                        "tipo":              "BLOQUEIO_CRUZAMENTO",
                        "descricao":         f"Bloqueio de cruzamento há {secs:.1f}s",
                        "track_id":          track.id,
                        "classe":            track.cls_name,
                        "bbox":              track.current["bbox"],
                        "frame":             frame_idx,
                        "timestamp":         datetime.datetime.now().isoformat(),
                        "confianca":         round(track.current.get("conf", 0.0), 3),
                        "segundos_bloqueio": round(secs, 1),
                    })
            else:
                self._inside_since.pop(track.id, None)

        return infractions

    def draw(self, frame, tracks: list, frame_idx: int):
        """Desenha polígonos do cruzamento e timer nos veículos bloqueadores."""
        overlay = frame.copy()
        for poly in self.polygons:
            pts = np.array(poly.get("points", []), np.int32)
            if len(pts) >= 3:
                cv2.fillPoly(overlay, [pts], (0, 80, 255))
                cv2.polylines(frame, [pts.reshape(-1,1,2)], True, (0,100,255), 2)
        cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)

        # Label de zona
        for poly in self.polygons:
            pts = np.array(poly.get("points", []), np.int32)
            if len(pts) >= 3:
                cx = int(pts[:,0].mean()); cy = int(pts[:,1].mean())
                label = f"[ {poly.get('name','CRUZAMENTO')} ]"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(frame, (cx-tw//2-4, cy-th-4), (cx+tw//2+4, cy+4), (0,0,0), -1)
                cv2.putText(frame, label, (cx-tw//2, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,100,255), 1, cv2.LINE_AA)

        # Timers nos veículos bloqueadores
        for track in tracks:
            if track.id not in self._inside_since or track.current is None:
                continue
            frames_in = frame_idx - self._inside_since[track.id]
            secs = frames_in / self.fps
            x1, y1, x2, y2 = track.current["bbox"]
            frac = min(1.0, frames_in / self.threshold_frames)
            r = int(255 * frac); g = int(165 * (1 - frac))
            color = (0, g, r)
            label = f"BLOQUEIO {secs:.1f}s"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y2+2), (x1+tw+4, y2+th+8), (0,0,0), -1)
            cv2.putText(frame, label, (x1+2, y2+th+4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
        return frame
