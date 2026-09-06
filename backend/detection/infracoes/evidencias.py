"""
Módulo de Evidências: salva screenshots e mini-clips das infrações.
Buffer circular mantém frames recentes para incluir contexto antes do evento.
"""
from __future__ import annotations
import os
import cv2
import time
import datetime
import itertools
import threading
from collections import deque

from backend.detection.limpeza import limpar_evidencias_antigas

_clip_id_counter = itertools.count()


class GerenciadorEvidencias:
    """Salva screenshots e mini-clips (pré + pós evento) das infrações."""

    def __init__(self,
                 output_dir: str,
                 fps: float = 30.0,
                 buffer_seconds: float = 3.0,
                 post_seconds:   float = 2.0):
        self.fps         = max(fps, 1.0)
        self.buffer_size = int(buffer_seconds * fps)
        self.post_size   = int(post_seconds   * fps)

        self.screenshots_dir = os.path.join(output_dir, "screenshots")
        self.clips_dir       = os.path.join(output_dir, "clips")
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.clips_dir,       exist_ok=True)

        # Buffer circular de frames anotados (pré-evento)
        self._frame_buffer: deque = deque(maxlen=self.buffer_size)
        # Clips aguardando frames futuros
        self._pending: list[dict] = []
        self._lock = threading.Lock()

    # ── API pública ───────────────────────────────────────────────────────────

    def push_frame(self, frame):
        """Deve ser chamado com cada frame processado para manter o buffer."""
        with self._lock:
            self._frame_buffer.append(frame.copy())
            for clip in self._pending:
                if len(clip["frames"]) < clip["frames_needed"]:
                    clip["frames"].append(frame.copy())

    def registrar(self, infracao: dict, frame) -> dict:
        """
        Salva screenshot imediato e inicia coleta assíncrona do mini-clip.
        Retorna dict com os caminhos dos arquivos.
        """
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        tipo = infracao.get("tipo", "INFRACAO").replace(" ", "_")
        tid  = infracao.get("track_id", 0)

        # ── Screenshot ────────────────────────────────────────────────────────
        ss_name = f"{tipo}_{ts}_ID{tid}.jpg"
        ss_path = os.path.join(self.screenshots_dir, ss_name)
        annotated = self._draw_overlay(frame.copy(), infracao)
        cv2.imwrite(ss_path, annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])

        # ── Mini-clip ─────────────────────────────────────────────────────────
        with self._lock:
            pre_frames = list(self._frame_buffer)
            clip_data  = {
                "id":            next(_clip_id_counter),
                "frames":        pre_frames,
                "frames_needed": self.buffer_size + self.post_size,
                "meta":          {"tipo": tipo, "ts": ts, "tid": tid},
                "path":          None,
            }
            self._pending.append(clip_data)

        threading.Thread(
            target=self._save_clip,
            args=(clip_data,),
            daemon=True,
        ).start()

        return {"screenshot": ss_path, "clip": "pendente"}

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _save_clip(self, clip_data: dict):
        """Aguarda frames futuros e grava o clip em MP4."""
        max_wait = (self.post_size / self.fps) + 3.0
        deadline = time.time() + max_wait
        while time.time() < deadline:
            with self._lock:
                ready = len(clip_data["frames"]) >= clip_data["frames_needed"]
            if ready:
                break
            time.sleep(0.05)

        meta      = clip_data["meta"]
        clip_name = f"{meta['tipo']}_{meta['ts']}_ID{meta['tid']}.mp4"
        clip_path = os.path.join(self.clips_dir, clip_name)

        frames = clip_data["frames"]
        if not frames:
            with self._lock:
                self._pending = [c for c in self._pending if c.get("id") != clip_data.get("id")]
            return

        h, w  = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(clip_path, fourcc, self.fps, (w, h))
        for f in frames:
            writer.write(f)
        writer.release()
        clip_data["path"] = clip_path

        with self._lock:
            self._pending = [c for c in self._pending if c.get("id") != clip_data.get("id")]

    def _draw_overlay(self, frame, infracao: dict):
        """Adiciona barra de status e destaque do veículo no screenshot."""
        tipo = infracao.get("tipo", "INFRAÇÃO")
        desc = infracao.get("descricao", "")
        ts   = infracao.get("timestamp", "")[:19]

        # Barra topo
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 58), (0, 0, 160), -1)
        cv2.putText(frame, f"INFRACAO: {tipo.replace('_',' ')}",
                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255,255,255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"{desc}  |  {ts}",
                    (10, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200,200,200), 1, cv2.LINE_AA)

        # Caixa do veículo
        bbox = infracao.get("bbox")
        if bbox:
            x1, y1, x2, y2 = bbox
            cv2.rectangle(frame, (x1,y1),(x2,y2), (0,0,255), 3)

        return frame
