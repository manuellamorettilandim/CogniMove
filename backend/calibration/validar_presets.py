#!/usr/bin/env python3
"""
CogniMove — Validador Automático de Presets e Fontes de Vídeo

Lê os pares (vídeo, preset) do arquivo BANCO_VIDEOS.md, executa a validação geométrica
e lógica dos presets, processa 400 quadros a partir de 35% de cada vídeo e salva um JPG
com todas as zonas desenhadas em backend/calibration/scratch_frames/.
"""
from __future__ import annotations

import os
import sys
import math
import re
import json
import cv2
import numpy as np
from pathlib import Path

# ── Ajustar sys.path ──────────────────────────────────────────────────────────
_HERE    = Path(__file__).resolve().parent   # calibration/
_BACKEND = _HERE.parent                      # backend/
_ROOT    = _BACKEND.parent                   # Cognimove_Melissa/

sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "detection"))

from utils_video import resolver_fonte_video
from infracoes.detector import InfracaoDetector, load_preset, scale_preset
from infracoes.regras.faixa_pedestre import segments_intersect
from calibration.calibrar_camera import polygon_is_self_intersecting

# ── Cores ANSI para saída do terminal ──────────────────────────────────────────
COLOR_RED   = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_RESET = "\033[0m"


def print_red(msg: str):
    print(f"{COLOR_RED}{msg}{COLOR_RESET}")


def parse_banco_videos(md_path: Path) -> list[tuple[str, str]]:
    """Extrai pares (nome_video, nome_preset) do BANCO_VIDEOS.md."""
    if not md_path.exists():
        print_red(f"[ERRO] Arquivo {md_path} não encontrado!")
        return []

    items = []
    content = md_path.read_text(encoding="utf-8")
    for line in content.splitlines():
        line_str = line.strip()
        if line_str.startswith("|") and not line_str.startswith("|---") and "Vídeo" not in line_str:
            cols = [c.strip() for c in line_str.split("|")[1:-1]]
            if len(cols) >= 2:
                video_name, preset_name = cols[0], cols[1]
                items.append((video_name, preset_name))
    return items


def validar_geometria_e_regras(preset_name: str, raw_preset: dict) -> list[str]:
    """Executa verificações geométricas e de regras no preset bruto."""
    alertas = []
    lines                 = raw_preset.get("lines", [])
    stop_lines            = raw_preset.get("stop_lines", [])
    polygons              = raw_preset.get("polygons", [])
    intersection_polygons = raw_preset.get("intersection_polygons", [])
    ref_w                 = raw_preset.get("ref_width", 1920)

    # 1. stop_lines vazio
    if len(stop_lines) == 0:
        alertas.append(f"Preset '{preset_name}': 'stop_lines' está vazio (avanço de sinal vermelho fica impossível).")

    # 2. polygons ou intersection_polygons vazios
    if len(polygons) == 0:
        alertas.append(f"Preset '{preset_name}': 'polygons' está vazio (faixas de pedestres/bike boxes não delimitadas).")
    if len(intersection_polygons) == 0:
        alertas.append(f"Preset '{preset_name}': 'intersection_polygons' está vazio (zona de cruzamento não delimitada).")

    # 3. Geometria de polígonos
    todos_poligonos = [("poligono_faixa", p) for p in polygons] + [("intersecao", p) for p in intersection_polygons]
    for tipo, poly in todos_poligonos:
        pname = poly.get("name", tipo)
        pts = poly.get("points", [])
        
        if len(pts) < 4:
            alertas.append(f"Preset '{preset_name}': Polígono '{pname}' tem menos de 4 pontos ({len(pts)}).")
        
        if len(pts) != len(set(tuple(pt) for pt in pts)):
            alertas.append(f"Preset '{preset_name}': Polígono '{pname}' contém pontos repetidos.")
            
        if polygon_is_self_intersecting(pts):
            alertas.append(f"Preset '{preset_name}': Polígono '{pname}' possui arestas que se cruzam (auto-intersecção).")

    # 4. Sobreposição de polígono de faixa com interseção (> 50% dos pontos dentro)
    for poly in polygons:
        pname = poly.get("name", "Faixa")
        pts = poly.get("points", [])
        if not pts:
            continue
        for int_poly in intersection_polygons:
            int_name = int_poly.get("name", "Interseção")
            int_pts = np.array(int_poly.get("points", []), dtype=np.int32)
            if len(int_pts) < 3:
                continue
            inside_count = sum(
                1 for pt in pts
                if cv2.pointPolygonTest(int_pts, (float(pt[0]), float(pt[1])), False) >= 0
            )
            if (inside_count / len(pts)) > 0.5:
                alertas.append(
                    f"Preset '{preset_name}': Polígono '{pname}' tem mais de 50% dos pontos dentro "
                    f"da zona de interseção '{int_name}' (zonas sobrepostas geram infração dupla)."
                )

    # 5. Comprimento de linha menor que 5% da largura
    min_len = ref_w * 0.05
    todas_linhas = [("linha_faixa", l) for l in lines] + [("linha_retencao", l) for l in stop_lines]
    for tipo, line in todas_linhas:
        lname = line.get("name", tipo)
        pt1, pt2 = line.get("pt1"), line.get("pt2")
        if pt1 and pt2:
            dx = pt2[0] - pt1[0]
            dy = pt2[1] - pt1[1]
            length = math.sqrt(dx * dx + dy * dy)
            if length < min_len:
                alertas.append(
                    f"Preset '{preset_name}': Linha '{lname}' tem comprimento ({length:.1f}px) "
                    f"menor que 5% da largura da imagem ({min_len:.1f}px)."
                )

    return alertas


def desenhar_overlay_preset(frame: np.ndarray, scaled_preset: dict) -> np.ndarray:
    """Desenha todas as formas do preset escalado sobre uma cópia do frame."""
    out = frame.copy()

    # Interseções (Ciano)
    for poly in scaled_preset.get("intersection_polygons", []):
        pts = np.array(poly.get("points", []), dtype=np.int32)
        if len(pts) >= 3:
            cv2.polylines(out, [pts], True, (255, 255, 0), 2)
            cv2.putText(out, poly.get("name", "Intersecao"), tuple(pts[0]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

    # Polígonos de faixa (Laranja)
    for poly in scaled_preset.get("polygons", []):
        pts = np.array(poly.get("points", []), dtype=np.int32)
        if len(pts) >= 3:
            cv2.polylines(out, [pts], True, (0, 165, 255), 2)
            cv2.putText(out, poly.get("name", "Faixa"), tuple(pts[0]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)

    # Linhas de Faixa/Limite (Amarelo)
    for l in scaled_preset.get("lines", []):
        pt1, pt2 = tuple(l["pt1"]), tuple(l["pt2"])
        cv2.line(out, pt1, pt2, (0, 255, 255), 2)

    # Linhas de Retenção (Vermelho)
    for l in scaled_preset.get("stop_lines", []):
        pt1, pt2 = tuple(l["pt1"]), tuple(l["pt2"])
        cv2.line(out, pt1, pt2, (0, 0, 255), 2)

    return out


def main():
    banco_md = _ROOT / "backend" / "calibration" / "presets" / "BANCO_VIDEOS.md"
    scratch_dir = _ROOT / "backend" / "calibration" / "scratch_frames"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    pares = parse_banco_videos(banco_md)
    if not pares:
        print_red("[FALHA] Nenhum par de vídeo/preset válido foi encontrado no BANCO_VIDEOS.md.")
        sys.exit(1)

    print("=" * 80)
    print("  CogniMove — Validador Automático de Presets e Fontes de Vídeo")
    print("=" * 80 + "\n")

    tabela_resultados = []

    for video_name, preset_name in pares:
        print(f"\n▶ Validando Preset: '{preset_name}' | Vídeo: '{video_name}'...")
        
        # 1. Carregar preset bruto
        raw_preset = load_preset(preset_name)
        
        # 2. Executar verificações de geometria e regras
        alertas_geometria = validar_geometria_e_regras(preset_name, raw_preset)
        for al in alertas_geometria:
            print_red(f"  [AVISO VERMELHO] {al}")

        # 3. Resolver caminho do vídeo
        video_path = resolver_fonte_video(video_name, root=_ROOT)
        if not Path(video_path).exists():
            print_red(f"  [AVISO VERMELHO] Arquivo de vídeo '{video_name}' não encontrado em {video_path}!")
            continue

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print_red(f"  [AVISO VERMELHO] Não foi possível abrir o vídeo '{video_path}'.")
            continue

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        start_frame = int(total_frames * 0.35)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        # Capturar o quadro a 35% para salvar no scratch_frames
        ret, frame_35 = cap.read()
        if ret:
            scaled_p = scale_preset(raw_preset, w, h)
            overlay = desenhar_overlay_preset(frame_35, scaled_p)
            scratch_path = scratch_dir / f"{preset_name}.jpg"
            cv2.imwrite(str(scratch_path), overlay)
            print(f"  [Scratch Frame] Quadro com overlay salvo em: {scratch_path}")
            # Voltar o leitor para o quadro de 35% para o InfracaoDetector
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        # 4. Instanciar Detector e processar 400 quadros
        detector = InfracaoDetector(
            source=video_path,
            preset_name=preset_name,
            show_window=False
        )
        detector._setup(w, h, fps)

        frames_processados = 0
        unknown_light_count = 0
        counts_infracoes = {"AVANCO_SINAL_VERMELHO": 0, "INVASAO_FAIXA": 0, "BLOQUEIO_CRUZAMENTO": 0}

        while frames_processados < 400:
            r, frame = cap.read()
            if not r:
                break
            frames_processados += 1

            annotated, infractions = detector._process_frame(frame)
            
            # Checar semáforo
            state = detector.regra_sinal.get_light_state() if detector.regra_sinal else "unknown"
            if state == "unknown":
                unknown_light_count += 1

            for inf in infractions:
                tipo = inf["tipo"]
                counts_infracoes[tipo] = counts_infracoes.get(tipo, 0) + 1

        cap.release()

        # Rule 6: Estado do semáforo "unknown" > 90%
        if frames_processados > 0:
            pct_unknown = (unknown_light_count / frames_processados) * 100
            if pct_unknown > 90.0:
                print_red(
                    f"  [AVISO VERMELHO] Preset '{preset_name}': Estado do semáforo ficou 'unknown' "
                    f"em {unknown_light_count}/{frames_processados} quadros ({pct_unknown:.1f}% > 90%)."
                )

        # Salvar dados para tabela final
        tabela_resultados.append({
            "preset": preset_name,
            "linhas": len(raw_preset.get("lines", [])),
            "retencoes": len(raw_preset.get("stop_lines", [])),
            "poligonos": len(raw_preset.get("polygons", [])),
            "intersecoes": len(raw_preset.get("intersection_polygons", [])),
            "avanco": counts_infracoes.get("AVANCO_SINAL_VERMELHO", 0),
            "invasao": counts_infracoes.get("INVASAO_FAIXA", 0),
            "bloqueio": counts_infracoes.get("BLOQUEIO_CRUZAMENTO", 0),
            "total_infr": sum(counts_infracoes.values()),
            "frames": frames_processados
        })

    # ── Imprimir Tabela Resumo ─────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("  TABELA RESUMO DE VALIDAÇÃO DE PRESETS (400 QUADROS A PARTIR DE 35% DO VÍDEO)")
    print("=" * 90)
    header = f"| {'Preset':<18} | {'Linhas':<6} | {'Retenções':<9} | {'Polígonos':<9} | {'Interseções':<11} | {'Avanço Sinal':<12} | {'Invasão Faixa':<13} | {'Bloqueio Cruz.':<14} |"
    print(header)
    print("|" + "-" * 20 + "|" + "-" * 8 + "|" + "-" * 11 + "|" + "-" * 11 + "|" + "-" * 13 + "|" + "-" * 14 + "|" + "-" * 15 + "|" + "-" * 16 + "|")

    for row in tabela_resultados:
        print(f"| {row['preset']:<18} | {row['linhas']:<6} | {row['retencoes']:<9} | {row['poligonos']:<9} | {row['intersecoes']:<11} | {row['avanco']:<12} | {row['invasao']:<13} | {row['bloqueio']:<14} |")

    print("=" * 90 + "\n")


if __name__ == "__main__":
    main()
