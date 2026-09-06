#!/usr/bin/env python3
"""
CogniMove — Ferramenta de Calibração Interativa de Câmera
Clique nos pontos do frame para definir linhas e zonas, depois salve o preset.

Controles:
  L  — modo Linha de Faixa/Limite (RegraFaixaPedestre)
  R  — modo Linha de Retenção Semafórica (RegraSinalVermelho)
  P  — modo Polígono (bike box / faixa)
  I  — modo Interseção (cruzamento)
  Z  — desfazer último ponto em edição
  X  — remover última forma concluída do modo atual
  C  — limpar seleção atual
  S  — salvar preset e sair
  Q  — sair sem salvar
"""
import os, sys, cv2, json, argparse, datetime, shutil
from pathlib import Path

_HERE    = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
_ROOT    = _BACKEND.parent

sys.path.insert(0, str(_BACKEND / "detection"))
from utils_video import resolver_fonte_video
from infracoes.regras.faixa_pedestre import segments_intersect


def polygon_is_self_intersecting(points: list) -> bool:
    """
    Verifica se o polígono possui autointerseção (arestas não-adjacentes que se cruzam).

    Args:
        points: Lista de pontos [x, y] ou (x, y) representando os vértices do polígono.

    Returns:
        True se houver autointerseção, False caso contrário.
    """
    n = len(points)
    if n < 4:
        return False

    edges = [(points[i], points[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            # Arestas adjacentes compartilham vértices: (i, i+1) ou (0, n-1)
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if segments_intersect(edges[i][0], edges[i][1], edges[j][0], edges[j][1]):
                return True
    return False


COLORS = {
    "line":         (0,   255, 255),  # Ciano/Amarelo (Linha de Faixa)
    "stop_line":    (0,   0,   255),  # Vermelho (Linha de Retenção Semafórica)
    "polygon":      (255, 200,   0),
    "intersection": (0,   100, 255),
}

MODES = ["line", "stop_line", "polygon", "intersection"]
MODE_LABELS = {
    "line":         "L — LINHA DE FAIXA/LIMITE (pedestre)",
    "stop_line":    "R — LINHA DE RETENCAO (semaforo)",
    "polygon":      "P — POLIGONO (bike box / faixa)",
    "intersection": "I — ZONA DE CRUZAMENTO",
}


class CalibradorCamera:
    def __init__(self, source, preset_name: str, output_dir: Path):
        self.source      = source
        self.preset_name = preset_name
        self.output_dir  = output_dir

        self.lines:         list[list] = []   # Linhas de faixa/limite (RegraFaixaPedestre)
        self.stop_lines:    list[list] = []   # Linhas de retenção (RegraSinalVermelho)
        self.polygons:      list[list] = []   # cada item: lista de N pontos
        self.intersections: list[list] = []   # cada item: lista de N pontos

        self.mode         = "line"
        self.current_pts: list        = []
        self.frame_orig   = None
        self.warning_msg: str | None  = None
        self.wname        = "CogniMove — Calibracao de Camera"

    # ── Captura do frame de referência ───────────────────────────────────────

    def _grab_frame(self):
        src = resolver_fonte_video(self.source, root=_ROOT)
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            print(f"[Erro] Não foi possível abrir: {self.source} (resolvido como: {src})")
            sys.exit(1)
        # Pular para 10% da duração (mais representativo que frame 0)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total > 10:
            cap.set(cv2.CAP_PROP_POS_FRAMES, total // 10)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            print("[Erro] Não foi possível ler frame.")
            sys.exit(1)
        return frame

    # ── Callback do mouse ─────────────────────────────────────────────────────

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.current_pts.append([x, y])
            # Linha de faixa: completa com 2 pontos
            if self.mode == "line" and len(self.current_pts) == 2:
                self.lines.append(list(self.current_pts))
                print(f"  [+] Linha de faixa adicionada: {self.current_pts}")
                self.current_pts = []
            # Linha de retenção: completa com 2 pontos
            elif self.mode == "stop_line" and len(self.current_pts) == 2:
                self.stop_lines.append(list(self.current_pts))
                print(f"  [+] Linha de retenção adicionada: {self.current_pts}")
                self.current_pts = []
        elif event == cv2.EVENT_RBUTTONDOWN:
            # Clique direito: fechar polígono/interseção
            if self.mode == "polygon" and len(self.current_pts) >= 3:
                if polygon_is_self_intersecting(self.current_pts):
                    self.warning_msg = "Polígono pode estar autointersectante — revise os pontos."
                    print(f"  [!] {self.warning_msg}")
                else:
                    self.warning_msg = None
                self.polygons.append(list(self.current_pts))
                print(f"  [+] Polígono ({len(self.current_pts)} pts) adicionado.")
                self.current_pts = []
            elif self.mode == "intersection" and len(self.current_pts) >= 3:
                if polygon_is_self_intersecting(self.current_pts):
                    self.warning_msg = "Polígono de cruzamento pode estar autointersectante — revise os pontos."
                    print(f"  [!] {self.warning_msg}")
                else:
                    self.warning_msg = None
                self.intersections.append(list(self.current_pts))
                print(f"  [+] Zona de cruzamento ({len(self.current_pts)} pts) adicionada.")
                self.current_pts = []

    # ── Remoção de formas concluídas ──────────────────────────────────────────

    def remover_ultima_forma(self) -> list | None:
        """Remove a última forma concluída da lista correspondente ao modo atual."""
        self.warning_msg = None
        lista = {
            "line":         self.lines,
            "stop_line":    self.stop_lines,
            "polygon":      self.polygons,
            "intersection": self.intersections,
        }.get(self.mode)
        if lista:
            removido = lista.pop()
            print(f"  [X] Última forma removida do modo '{self.mode}': {removido}")
            return removido
        print(f"  [X] Nenhuma forma para remover no modo '{self.mode}'.")
        return None

    # ── Renderização ──────────────────────────────────────────────────────────

    def _render(self, frame):
        import numpy as np
        disp = frame.copy()

        # Linhas de faixa salvas
        for pts in self.lines:
            cv2.line(disp, tuple(pts[0]), tuple(pts[1]), COLORS["line"], 2)
            cv2.circle(disp, tuple(pts[0]), 5, COLORS["line"], -1)
            cv2.circle(disp, tuple(pts[1]), 5, COLORS["line"], -1)

        # Linhas de retenção salvas
        for pts in self.stop_lines:
            cv2.line(disp, tuple(pts[0]), tuple(pts[1]), COLORS["stop_line"], 2)
            cv2.circle(disp, tuple(pts[0]), 5, COLORS["stop_line"], -1)
            cv2.circle(disp, tuple(pts[1]), 5, COLORS["stop_line"], -1)

        # Polígonos salvos
        for pts in self.polygons:
            poly = np.array(pts, np.int32)
            cv2.polylines(disp, [poly.reshape(-1,1,2)], True, COLORS["polygon"], 2)
            for p in pts:
                cv2.circle(disp, tuple(p), 4, COLORS["polygon"], -1)

        # Interseções salvas
        for pts in self.intersections:
            poly = np.array(pts, np.int32)
            cv2.polylines(disp, [poly.reshape(-1,1,2)], True, COLORS["intersection"], 2)
            for p in pts:
                cv2.circle(disp, tuple(p), 4, COLORS["intersection"], -1)

        # Pontos correntes
        cur_color = COLORS.get(self.mode, (255, 255, 255))
        for p in self.current_pts:
            cv2.circle(disp, tuple(p), 5, cur_color, -1)
        if len(self.current_pts) >= 2:
            import numpy as np
            pts_np = np.array(self.current_pts, np.int32)
            cv2.polylines(disp, [pts_np.reshape(-1,1,2)], False, cur_color, 1)

        # HUD
        h, w = disp.shape[:2]
        hud_h = 74 if self.warning_msg else 54
        cv2.rectangle(disp, (0,0),(w,hud_h),(10,10,10),-1)
        mode_lbl = MODE_LABELS.get(self.mode,"")
        cv2.putText(disp,f"MODO: {mode_lbl}",(8,20),
                    cv2.FONT_HERSHEY_SIMPLEX,0.52,cur_color,1,cv2.LINE_AA)
        cv2.putText(disp,
                    f"Faixa:{len(self.lines)}  Retencao:{len(self.stop_lines)}  "
                    f"Poligonos:{len(self.polygons)}  Cruzamentos:{len(self.intersections)}  "
                    f"Pts atuais:{len(self.current_pts)}  "
                    f"[L/R/P/I=modo  Z=desfazer pt  X=remover forma  C=limpar  S=salvar  Q=sair]",
                    (8,42),cv2.FONT_HERSHEY_SIMPLEX,0.36,(180,180,180),1,cv2.LINE_AA)
        if self.warning_msg:
            cv2.putText(disp, f"[!] {self.warning_msg}", (8,62),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0,0,255), 1, cv2.LINE_AA)
        return disp

    # ── Salvar preset ────────────────────────────────────────────────────────

    def _save(self, width: int, height: int):
        # Nota de compatibilidade:
        # Presets gerados anteriormente duplicavam self.lines em "stop_lines".
        # Agora as duas geometrias são independentes:
        #  - "lines" alimenta RegraFaixaPedestre (INVASAO_FAIXA)
        #  - "stop_lines" alimenta RegraSinalVermelho (AVANCO_SINAL_VERMELHO)
        preset = {
            "name":        self.preset_name,
            "ref_width":   width,
            "ref_height":  height,
            "lines": [
                {"name": f"Linha {i+1}", "pt1": pts[0], "pt2": pts[1],
                 "color": [0,255,255]}
                for i, pts in enumerate(self.lines)
            ],
            "stop_lines": [
                {"name": f"Retencao {i+1}", "pt1": pts[0], "pt2": pts[1],
                 "color": [0,0,255]}
                for i, pts in enumerate(self.stop_lines)
            ],
            "polygons": [
                {"name": f"Area {i+1}", "type": "bike_box", "points": pts}
                for i, pts in enumerate(self.polygons)
            ],
            "intersection_polygons": [
                {"name": f"Cruzamento {i+1}", "type": "intersection", "points": pts}
                for i, pts in enumerate(self.intersections)
            ],
        }
        out_path = self.output_dir / f"{self.preset_name}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists():
            resposta = input(
                f"\n[Aviso] Preset '{self.preset_name}' já existe em {out_path}. "
                f"Sobrescrever? [s/N] "
            ).strip().lower()
            if resposta != "s":
                print("[Cancelado] Preset não foi salvo.")
                return None

            # Backup com timestamp antes de sobrescrever
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            bak_path = self.output_dir / f"{self.preset_name}.json.bak.{ts}"
            try:
                shutil.copy2(out_path, bak_path)
                print(f"[Backup] Cópia de segurança criada em: {bak_path}")
            except Exception as e:
                print(f"[Aviso] Falha ao criar backup: {e}")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(preset, f, ensure_ascii=False, indent=2)
        print(f"\n[Salvo] Preset '{self.preset_name}' em: {out_path}")
        return out_path

    # ── Loop principal ────────────────────────────────────────────────────────

    def run(self):
        print("\n=== CogniMove — Calibração de Câmera ===")
        print("  L = linha de faixa/limite  |  R = linha de retenção (semáforo)  |  P = polígono  |  I = interseção")
        print("  Clique esquerdo = adicionar ponto")
        print("  Clique direito  = fechar polígono/interseção")
        print("  Z = desfazer ponto  |  X = remover última forma  |  C = limpar  |  S = salvar  |  Q = sair")

        frame = self._grab_frame()
        h, w  = frame.shape[:2]
        print(f"[Info] Resolução: {w}x{h}")

        cv2.namedWindow(self.wname, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.wname, self._on_mouse)

        while True:
            disp = self._render(frame)
            cv2.imshow(self.wname, disp)
            key = cv2.waitKey(30) & 0xFF

            if key == ord("l"):
                self.mode = "line";         self.current_pts = []
                print("[Modo] Linha de faixa/limite (pedestre)")
            elif key == ord("r"):
                self.mode = "stop_line";    self.current_pts = []
                print("[Modo] Linha de retenção (semáforo)")
            elif key == ord("p"):
                self.mode = "polygon";      self.current_pts = []
                print("[Modo] Polígono (bike box / faixa)")
            elif key == ord("i"):
                self.mode = "intersection"; self.current_pts = []
                print("[Modo] Zona de cruzamento")
            elif key == ord("z") and self.current_pts:
                removed = self.current_pts.pop()
                print(f"  [-] Ponto removido: {removed}")
            elif key == ord("x"):
                self.remover_ultima_forma()
            elif key == ord("c"):
                self.current_pts = []
                self.warning_msg = None
                print("  [C] Pontos correntes limpos")
            elif key == ord("s"):
                path = self._save(w, h)
                if path is not None:
                    print(f"[OK] Preset salvo. Use --preset {self.preset_name} ao monitorar.")
                    break
                else:
                    print("[Info] Retornando ao modo de calibração.")
            elif key in (ord("q"), 27):
                print("[Q] Saindo sem salvar.")
                break

        cv2.destroyAllWindows()


def main():
    p = argparse.ArgumentParser(description="Calibração interativa de câmera — CogniMove")
    p.add_argument("--source",  "-s", default=None,
                   help="Fonte de vídeo (0, rtsp://, arquivo)")
    p.add_argument("--preset",  "-p", default="minha_camera",
                   help="Nome do preset a salvar (sem .json)")
    args = p.parse_args()

    source = args.source
    if source is None:
        # Busca automática
        import glob as _glob
        videos = list((_ROOT / "videos_teste").glob("*.mp4")) + \
                 list((_ROOT / "videos_originais").glob("*.mp4"))
        if videos:
            videos.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            source = str(videos[0])
            print(f"[Auto] Usando: {source}")
        else:
            source = "0"
            print("[Auto] Nenhum vídeo encontrado, usando webcam 0")

    out_dir = _ROOT / "backend" / "calibration" / "presets"
    cal = CalibradorCamera(source, args.preset, out_dir)
    cal.run()


if __name__ == "__main__":
    main()
