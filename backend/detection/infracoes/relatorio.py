"""
Módulo de Relatório: registra infrações em CSV e JSON de forma thread-safe.
"""
from __future__ import annotations
import os
import csv
import json
import datetime
import threading


class GerenciadorRelatorio:
    """Grava infrações em CSV e JSON em modo append, thread-safe."""

    CAMPOS = [
        "timestamp", "frame", "tipo", "descricao",
        "track_id", "classe", "confianca", "camera",
        "screenshot", "clip",
        # Campos do Módulo 2 — Análise de Causa-Raiz
        "causa_principal", "causa_confianca",
        "cenarios_ativos", "distribuicao_causas",
    ]

    def __init__(self, output_dir: str, camera_name: str = "camera"):
        self.camera_name = camera_name
        os.makedirs(output_dir, exist_ok=True)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path  = os.path.join(output_dir, f"infracoes_{ts}.csv")
        self.json_path = os.path.join(output_dir, f"infracoes_{ts}.json")

        self._lock    = threading.Lock()
        self._records: list[dict] = []

        # Criar CSV com cabeçalho
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=self.CAMPOS).writeheader()

        # JSON inicial vazio
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump([], f)

    # ── API pública ───────────────────────────────────────────────────────────

    def adicionar(self, infracao: dict, evidencias: dict = None,
                  analise_causa: dict = None):
        """Adiciona uma infração ao relatório (CSV + JSON).

        Args:
            infracao:       Dados da infração detectada.
            evidencias:     Caminhos de screenshot e clip gerados.
            analise_causa:  Resultado do MotorCausaRaiz.calcular_probabilidades().
        """
        ev = evidencias or {}
        ac = analise_causa or {}
        record = {
            "timestamp":  infracao.get("timestamp", datetime.datetime.now().isoformat()),
            "frame":      infracao.get("frame", 0),
            "tipo":       infracao.get("tipo", ""),
            "descricao":  infracao.get("descricao", ""),
            "track_id":   infracao.get("track_id", -1),
            "classe":     infracao.get("classe", ""),
            "confianca":  round(float(infracao.get("confianca", 0.0)), 3),
            "camera":     self.camera_name,
            "screenshot": ev.get("screenshot", ""),
            "clip":       ev.get("clip", ""),
            # Módulo 2 — Causa-Raiz
            "causa_principal":    ac.get("causa_principal", ""),
            "causa_confianca":    round(float(ac.get("confianca", 0.0)), 4),
            "cenarios_ativos":    ", ".join(ac.get("fatores_ativos", [])),
            "distribuicao_causas": json.dumps(ac.get("distribuicao", {}), ensure_ascii=False),
        }
        with self._lock:
            self._records.append(record)
            # Append no CSV
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=self.CAMPOS).writerow(record)
            # Reescrever JSON completo
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(self._records, f, ensure_ascii=False, indent=2)

    def get_records(self) -> list[dict]:
        with self._lock:
            return list(self._records)

    def get_stats(self) -> dict:
        with self._lock:
            stats: dict[str, int] = {"total": len(self._records)}
            for r in self._records:
                t = r.get("tipo", "OUTRO")
                stats[t] = stats.get(t, 0) + 1
            return stats
