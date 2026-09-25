"""
Módulo de Relatório: registra infrações em CSV e JSON de forma thread-safe.
"""
from __future__ import annotations
import os
import re
import csv
import json
import datetime
import threading


def _sanitizar_nome_arquivo(nome: str) -> str:
    """Sanitiza strings para nomes de arquivo seguros (apenas letras, dígitos, underline e hífen)."""
    return re.sub(r'[^A-Za-z0-9_-]', '_', nome)


class GerenciadorRelatorio:
    """Grava infrações em CSV e JSON Lines (.jsonl) em modo append, thread-safe."""

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

        cam_slug = _sanitizar_nome_arquivo(camera_name)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path   = os.path.join(output_dir, f"infracoes_{cam_slug}_{ts}.csv")
        self.jsonl_path = os.path.join(output_dir, f"infracoes_{cam_slug}_{ts}.jsonl")
        self.json_path  = self.jsonl_path  # Alias para compatibilidade com código consumidor existente

        self._lock    = threading.Lock()
        self._records: list[dict] = []

        # Criar CSV com cabeçalho
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=self.CAMPOS).writeheader()

        # Inicializar arquivo JSON Lines vazio
        with open(self.jsonl_path, "w", encoding="utf-8") as f:
            pass

    # ── API pública ───────────────────────────────────────────────────────────

    def adicionar(self, infracao: dict, evidencias: dict = None,
                  analise_causa: dict = None):
        """Adiciona uma infração ao relatório (CSV + JSON Lines em modo append).

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
            # Append O(1) no CSV
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=self.CAMPOS).writerow(record)
            # Append O(1) no JSON Lines (uma linha JSON por registro, sem reescrever o arquivo)
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def get_records(self, from_disk: bool = False) -> list[dict]:
        """Retorna os registros de infrações.

        Args:
            from_disk: Se True, lê e reconstrói a lista a partir do arquivo JSON Lines em disco.
                       Se False (padrão), retorna a cópia dos registros da sessão em memória.
        """
        with self._lock:
            if not from_disk:
                return list(self._records)

        # Leitura linha a linha do arquivo JSONL
        records = []
        if os.path.exists(self.jsonl_path):
            with open(self.jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        return records

    def get_stats(self) -> dict:
        with self._lock:
            stats: dict[str, int] = {"total": len(self._records)}
            for r in self._records:
                t = r.get("tipo", "OUTRO")
                stats[t] = stats.get(t, 0) + 1
            return stats

    @staticmethod
    def carregar_jsonl(caminho: str) -> list[dict]:
        """Carrega e desserializa um arquivo JSON Lines existente em disco."""
        registros = []
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            registros.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        return registros

    def exportar_json_tradicional(self, caminho_saida: str | None = None) -> str:
        """Exporta sob demanda todos os registros em um arquivo com array JSON tradicional."""
        if caminho_saida is None:
            caminho_saida = os.path.splitext(self.jsonl_path)[0] + ".json"
        with self._lock:
            data = list(self._records)
        with open(caminho_saida, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return caminho_saida
