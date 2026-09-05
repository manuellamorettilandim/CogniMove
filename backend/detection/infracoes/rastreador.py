"""
Rastreador de veículos usando ByteTrack (via YOLOv8 model.track()).
Mantém histórico de posições por ID para detectar cruzamentos de linha.
"""
import os
from collections import deque
from ultralytics import YOLO

# Classes COCO relevantes: person, bicycle, car, motorcycle, bus, truck
VEHICLE_CLASSES = [0, 1, 2, 3, 5, 7]
VEHICLE_NAMES   = {
    0: "Pedestre", 1: "Bicicleta", 2: "Carro",
    3: "Moto",     5: "Onibus",    7: "Caminhao",
}


class VehicleTrack:
    """Representa o estado atual e histórico de um veículo rastreado."""

    def __init__(self, track_id: int, cls_id: int, cls_name: str):
        self.id       = track_id
        self.cls_id   = cls_id
        self.cls_name = cls_name
        # Cada entrada: {frame, bbox, bottom_pt, centroid, conf}
        self.history: deque = deque(maxlen=150)  # ~5s a 30fps
        self.first_seen: int | None = None
        self.last_seen:  int | None = None
        self.active = True

    def update(self, frame_idx: int, bbox: tuple, conf: float):
        x1, y1, x2, y2 = bbox
        bottom_pt = ((x1 + x2) // 2, y2)
        centroid  = ((x1 + x2) // 2, (y1 + y2) // 2)
        self.history.append({
            "frame":     frame_idx,
            "bbox":      bbox,
            "bottom_pt": bottom_pt,
            "centroid":  centroid,
            "conf":      conf,
        })
        if self.first_seen is None:
            self.first_seen = frame_idx
        self.last_seen = frame_idx

    @property
    def current(self) -> dict | None:
        return self.history[-1] if self.history else None

    @property
    def previous(self) -> dict | None:
        return self.history[-2] if len(self.history) >= 2 else None


class Rastreador:
    """Gerencia o rastreamento de veículos usando YOLOv8 + ByteTrack."""

    def __init__(self, model_path: str):
        self.model = YOLO(model_path)
        self.tracks: dict[int, VehicleTrack] = {}
        self.frame_idx = 0

    def update(self, frame) -> list[VehicleTrack]:
        """
        Executa rastreamento no frame e retorna lista de VehicleTrack ativos.
        """
        self.frame_idx += 1
        results = self.model.track(
            frame,
            classes=VEHICLE_CLASSES,
            conf=0.25,
            persist=True,
            verbose=False,
            tracker="botsort.yaml",  # BoTSORT: não requer lap (usa scipy)
        )

        active_ids: set[int] = set()
        active_tracks: list[VehicleTrack] = []

        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                if box.id is None:
                    continue
                track_id = int(box.id[0])
                cls_id   = int(box.cls[0])
                conf     = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cls_name = VEHICLE_NAMES.get(
                    cls_id, self.model.names.get(cls_id, str(cls_id))
                )

                if track_id not in self.tracks:
                    self.tracks[track_id] = VehicleTrack(track_id, cls_id, cls_name)

                self.tracks[track_id].update(self.frame_idx, (x1, y1, x2, y2), conf)
                self.tracks[track_id].active = True
                active_ids.add(track_id)
                active_tracks.append(self.tracks[track_id])

        # Marcar tracks não vistos como inativos
        for tid, track in self.tracks.items():
            if tid not in active_ids:
                track.active = False

        return active_tracks

    def get_track(self, track_id: int) -> VehicleTrack | None:
        return self.tracks.get(track_id)
