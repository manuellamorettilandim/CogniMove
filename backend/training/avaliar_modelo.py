#!/usr/bin/env python3
"""
CogniMove — Script de Avaliação Manual e Medição de Cobertura do Modelo YOLOv8

Avalia a capacidade de generalização e cobertura do modelo de detecção de objetos
(backend/models/best.pt) em vídeos novos/não vistos ou datasets anotados de teste.

FUNCIONALIDADES:
  1. Processa um vídeo individual, uma pasta com múltiplos vídeos ou resolve nomes de vídeos do projeto.
  2. Computa métricas não-supervisionadas de cobertura e detecção:
      - Contagem de detecções por classe (Limite, Faixa_Pedestre, Semaforo, etc.)
      - Confiança média por classe
      - Contagem e porcentagem de frames sem nenhuma detecção (indicativo de baixa cobertura)
  3. Suporta avaliação supervisionada formal (model.val()) se um arquivo data.yaml de dataset anotado
     for fornecido via --data, utilizando as funções nativas de validação do Ultralytics para calcular
     Precision, Recall, mAP50 e mAP50-95.
  4. Exibe relatório formatado no console ao final da execução.
  5. Salva opcionalmente relatórios detalhados em CSV em backend/outputs/avaliacao_modelo/.

EXEMPLOS DE USO:
  # 1. Avaliar um vídeo específico:
  python backend/training/avaliar_modelo.py --fonte videos_teste/video_teste4.mp4

  # 2. Avaliar todos os vídeos em uma pasta e salvar relatório CSV:
  python backend/training/avaliar_modelo.py --fonte videos_originais/ --salvar-csv

  # 3. Avaliar com limiar de confiança customizado e salvar em CSV específico:
  python backend/training/avaliar_modelo.py --fonte video_teste.mp4 --conf 0.30 --salvar-csv relatorio.csv

  # 4. Executar validação supervisionada formal em dataset com anotações de referência (ground truth):
  python backend/training/avaliar_modelo.py --data backend/training/datasets/unificado/data.yaml

LIMITAÇÕES CONHECIDAS:
  Para calcular métricas formais de Precisão (Precision), Revocação (Recall) e mAP, é estritamente
  necessário possuir anotações de referência (ground truth) no formato YOLO (arquivos .txt rotulados).
  Ao avaliar vídeos brutos/novos sem um conjunto de anotações prévias, o cálculo de Precision/Recall
  não é realizável sem ground truth. Por essa razão, a análise nesses vídeos foca nos indicadores de
  inferência (contagens por classe, confiança média e taxa de frames sem detecção).
"""
import os
import sys
import csv
import argparse
import datetime
from pathlib import Path
from typing import Dict, Any, List

import cv2
from ultralytics import YOLO

# Ajustar sys.path para importação de utilitários do backend
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "detection"))

try:
    from utils_video import resolver_fonte_video, EXTENSOES_VIDEO
except ImportError:
    EXTENSOES_VIDEO = (".mp4", ".avi", ".mov", ".mkv", ".webm")
    def resolver_fonte_video(source, root=None):
        return source

# Caminhos padrão do projeto
DEFAULT_MODEL_PATH = PROJECT_ROOT / "backend" / "models" / "best.pt"
FALLBACK_MODEL_PATH = PROJECT_ROOT / "backend" / "models" / "yolov8n.pt"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "backend" / "outputs" / "avaliacao_modelo"


def localizar_arquivos_video(fonte: str) -> List[Path]:
    """
    Resolve a fonte fornecida para uma lista de caminhos de arquivos de vídeo existentes.
    Aceita arquivo individual, pasta contendo vídeos ou nome de arquivo do projeto.
    """
    path_obj = Path(fonte)

    # 1. Se for um diretório existente, varre os arquivos de vídeo contidos nele
    if path_obj.exists() and path_obj.is_dir():
        videos = [
            p for p in path_obj.iterdir()
            if p.is_file() and p.suffix.lower() in EXTENSOES_VIDEO
        ]
        return sorted(videos)

    # 2. Tentar resolver a fonte como arquivo único via resolver_fonte_video
    fonte_resolvida = resolver_fonte_video(fonte, root=PROJECT_ROOT)
    resolved_path = Path(fonte_resolvida)
    if resolved_path.exists() and resolved_path.is_file():
        return [resolved_path]

    # 3. Tentativa secundária: busca direta por nome dentro de videos_teste ou videos_originais
    for subfolder in ("videos_teste", "videos_originais"):
        candidato = PROJECT_ROOT / subfolder / path_obj.name
        if candidato.exists() and candidato.is_file():
            return [candidato]

    return []


def avaliar_video(
    model: YOLO,
    video_path: Path,
    conf_thresh: float = 0.25,
    iou_thresh: float = 0.45,
    max_frames: int | None = None,
    device: str = ""
) -> Dict[str, Any]:
    """
    Processa um arquivo de vídeo frame a frame e calcula as estatísticas de detecção.

    Returns:
        Dicionário com total_frames, frames_sem_deteccao, pct_frames_sem_deteccao,
        total_deteccoes, contagem_por_classe e confianca_media_por_classe.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"[ERRO] Não foi possível abrir o vídeo: {video_path}")
        return {}

    total_frames = 0
    frames_sem_deteccao = 0
    contagem_por_classe: Dict[str, int] = {}
    soma_confianca_por_classe: Dict[str, float] = {}

    # Inicializar contadores para todas as classes registradas no modelo
    for cls_id, cls_name in model.names.items():
        contagem_por_classe[cls_name] = 0
        soma_confianca_por_classe[cls_name] = 0.0

    print(f"\n[AVALIAÇÃO] Processando vídeo: {video_path.name}...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        total_frames += 1

        # Executar inferência no frame atual
        results = model.predict(
            source=frame,
            conf=conf_thresh,
            iou=iou_thresh,
            device=device if device else None,
            verbose=False
        )

        boxes = results[0].boxes if len(results) > 0 else []

        if len(boxes) == 0:
            frames_sem_deteccao += 1
        else:
            for box in boxes:
                cls_id = int(box.cls[0].item())
                conf_val = float(box.conf[0].item())
                cls_name = model.names.get(cls_id, f"classe_{cls_id}")

                contagem_por_classe[cls_name] = contagem_por_classe.get(cls_name, 0) + 1
                soma_confianca_por_classe[cls_name] = soma_confianca_por_classe.get(cls_name, 0.0) + conf_val

        if max_frames and total_frames >= max_frames:
            print(f"  [AVISO] Limite de {max_frames} frames atingido para {video_path.name}.")
            break

    cap.release()

    # Calcular médias de confiança por classe
    confianca_media_por_classe: Dict[str, float] = {}
    for cls_name, count in contagem_por_classe.items():
        if count > 0:
            confianca_media_por_classe[cls_name] = soma_confianca_por_classe[cls_name] / count
        else:
            confianca_media_por_classe[cls_name] = 0.0

    total_deteccoes = sum(contagem_por_classe.values())
    pct_sem_deteccao = (frames_sem_deteccao / total_frames * 100.0) if total_frames > 0 else 0.0

    return {
        "video": video_path.name,
        "caminho_completo": str(video_path),
        "total_frames": total_frames,
        "frames_sem_deteccao": frames_sem_deteccao,
        "pct_frames_sem_deteccao": pct_sem_deteccao,
        "total_deteccoes": total_deteccoes,
        "contagem_por_classe": contagem_por_classe,
        "confianca_media_por_classe": confianca_media_por_classe,
    }


def imprimir_relatorio_console(resultados: List[Dict[str, Any]], model_name: str, conf_thresh: float):
    """
    Imprime um resumo amigável e estruturado no terminal.
    """
    print("\n" + "=" * 78)
    print(f"  [CogniMove] Relatório de Avaliação do Modelo YOLOv8: {model_name}")
    print(f"  Limiar de Confiança: {conf_thresh:.2f}")
    print("=" * 78)

    if not resultados:
        print("  Nenhum vídeo foi avaliado.")
        print("=" * 78 + "\n")
        return

    global_total_frames = 0
    global_frames_sem_deteccao = 0
    global_total_deteccoes = 0
    global_contagem_classes: Dict[str, int] = {}
    global_soma_confianca: Dict[str, float] = {}

    for res in resultados:
        print(f"\n📹 VÍDEO: {res['video']}")
        print(f"   ├─ Total de Frames Processados : {res['total_frames']}")
        print(f"   ├─ Frames sem nenhuma detecção : {res['frames_sem_deteccao']} ({res['pct_frames_sem_deteccao']:.1f}%)")
        print(f"   ├─ Total de Objetos Detectados : {res['total_deteccoes']}")
        print("   └─ Detecções e Confiança Média por Classe:")

        for cls_name, count in res["contagem_por_classe"].items():
            conf_avg = res["confianca_media_por_classe"].get(cls_name, 0.0)
            if count > 0:
                print(f"       • {cls_name:<18}: {count:>5} detecções | Confiança Média: {conf_avg:.1%}")
            else:
                print(f"       • {cls_name:<18}:     0 detecções | Confiança Média:  N/A")

        # Acumular estatísticas globais
        global_total_frames += res["total_frames"]
        global_frames_sem_deteccao += res["frames_sem_deteccao"]
        global_total_deteccoes += res["total_deteccoes"]

        for cls_name, count in res["contagem_por_classe"].items():
            global_contagem_classes[cls_name] = global_contagem_classes.get(cls_name, 0) + count
            soma_conf = res["confianca_media_por_classe"].get(cls_name, 0.0) * count
            global_soma_confianca[cls_name] = global_soma_confianca.get(cls_name, 0.0) + soma_conf

    if len(resultados) > 1:
        pct_global_sem_det = (global_frames_sem_deteccao / global_total_frames * 100.0) if global_total_frames > 0 else 0.0
        print("\n" + "-" * 78)
        print("📊 RESUMO CONSOLIDADO (TODOS OS VÍDEOS):")
        print(f"   ├─ Vídeos Avaliados            : {len(resultados)}")
        print(f"   ├─ Total de Frames Processados : {global_total_frames}")
        print(f"   ├─ Total Frames sem Detecção   : {global_frames_sem_deteccao} ({pct_global_sem_det:.1f}%)")
        print(f"   ├─ Total Geral de Detecções    : {global_total_deteccoes}")
        print("   └─ Totais Globais por Classe:")

        for cls_name, count in global_contagem_classes.items():
            if count > 0:
                conf_avg = global_soma_confianca[cls_name] / count
                print(f"       • {cls_name:<18}: {count:>5} detecções | Confiança Média: {conf_avg:.1%}")
            else:
                print(f"       • {cls_name:<18}:     0 detecções | Confiança Média:  N/A")

    print("\n" + "=" * 78 + "\n")


def salvar_resultados_csv(resultados: List[Dict[str, Any]], output_path: Path):
    """
    Exporta a lista de resultados das avaliações dos vídeos em um arquivo CSV.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Identificar todas as classes presentes nos resultados
    todas_classes = sorted({
        cls_name
        for res in resultados
        for cls_name in res["contagem_por_classe"].keys()
    })

    fieldnames = [
        "video",
        "total_frames",
        "frames_sem_deteccao",
        "pct_frames_sem_deteccao",
        "total_deteccoes",
    ]
    for c in todas_classes:
        fieldnames.append(f"count_{c}")
        fieldnames.append(f"conf_avg_{c}")

    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for res in resultados:
            row = {
                "video": res["video"],
                "total_frames": res["total_frames"],
                "frames_sem_deteccao": res["frames_sem_deteccao"],
                "pct_frames_sem_deteccao": f"{res['pct_frames_sem_deteccao']:.2f}",
                "total_deteccoes": res["total_deteccoes"],
            }
            for c in todas_classes:
                cnt = res["contagem_por_classe"].get(c, 0)
                conf = res["confianca_media_por_classe"].get(c, 0.0)
                row[f"count_{c}"] = cnt
                row[f"conf_avg_{c}"] = f"{conf:.4f}" if cnt > 0 else "0.0000"

            writer.writerow(row)

    print(f"[SALVO] Relatório CSV de avaliação salvo com sucesso em:\n        {output_path.resolve()}")


def executar_validacao_supervisionada(model: YOLO, data_path: str, conf_thresh: float, iou_thresh: float, device: str = ""):
    """
    Executa a validação supervisionada formal via model.val() usando o dataset anotado.
    """
    print("\n" + "=" * 78)
    print("  [CogniMove] Executando Validação Supervisionada Formal (model.val())")
    print(f"  Dataset YAML: {data_path}")
    print("=" * 78)

    if not Path(data_path).exists():
        print(f"[ERRO] Arquivo de configuração de dataset não encontrado: {data_path}")
        return

    try:
        val_results = model.val(
            data=data_path,
            conf=conf_thresh,
            iou=iou_thresh,
            device=device if device else None,
            verbose=True
        )

        print("\n[RESULTADOS DA VALIDAÇÃO SUPERVISIONADA]")
        if hasattr(val_results, "results_dict"):
            metrics = val_results.results_dict
            print(f"  • Precision (mAP50-95 B): {metrics.get('metrics/precision(B)', 'N/A')}")
            print(f"  • Recall (mAP50-95 B)   : {metrics.get('metrics/recall(B)', 'N/A')}")
            print(f"  • mAP50                 : {metrics.get('metrics/mAP50(B)', 'N/A')}")
            print(f"  • mAP50-95              : {metrics.get('metrics/mAP50-95(B)', 'N/A')}")

    except Exception as e:
        print(f"[ERRO] Falha ao executar a validação supervisionada: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Avalia a cobertura e a precisão do modelo YOLOv8 do CogniMove em vídeos de teste ou datasets anotados."
    )
    parser.add_argument(
        "--fonte", "-f", "--video",
        type=str,
        default=None,
        help="Caminho para arquivo de vídeo, diretório com vídeos ou nome do vídeo (ex: video_teste4.mp4 ou videos_originais/)."
    )
    parser.add_argument(
        "--modelo", "-m",
        type=str,
        default=str(DEFAULT_MODEL_PATH),
        help=f"Caminho do modelo de pesos YOLO (.pt). Padrão: {DEFAULT_MODEL_PATH}"
    )
    parser.add_argument(
        "--data", "-d",
        type=str,
        default=None,
        help="Caminho para arquivo data.yaml anotado para executar validação supervisionada formal via model.val()."
    )
    parser.add_argument(
        "--conf", "-c",
        type=float,
        default=0.25,
        help="Limiar de confiança mínima para considerar uma detecção (0.0 a 1.0). Padrão: 0.25"
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.45,
        help="Limiar de IoU para NMS/validação. Padrão: 0.45"
    )
    parser.add_argument(
        "--salvar-csv",
        nargs="?",
        const="DEFAULT",
        default=None,
        help="Salva os resultados em CSV. Pode especificar o nome do arquivo ou usar padrão com timestamp."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Diretório para salvar o relatório CSV. Padrão: {DEFAULT_OUTPUT_DIR}"
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Limite máximo de frames a avaliar por vídeo (útil para testes rápidos em vídeos longos)."
    )
    parser.add_argument(
        "--device",
        type=str,
        default="",
        help="Dispositivo de execução ('cpu', '0', etc.). Deixe vazio para seleção automática."
    )

    args = parser.parse_args()

    # 1. Carregar Modelo
    model_path = Path(args.modelo)
    if not model_path.exists():
        if FALLBACK_MODEL_PATH.exists():
            print(f"[AVISO] Modelo {model_path} não encontrado. Utilizando fallback: {FALLBACK_MODEL_PATH}")
            model_path = FALLBACK_MODEL_PATH
        else:
            model_path_str = "yolov8n.pt"
            print(f"[AVISO] Pesos locais não encontrados. Utilizando fallback de modelo base: '{model_path_str}'")
            model_path = Path(model_path_str)

    print(f"[INICIALIZAÇÃO] Carregando modelo YOLO a partir de: {model_path}")
    try:
        model = YOLO(str(model_path))
    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha ao carregar o modelo YOLO: {e}")
        sys.exit(1)

    # 2. Se for solicitada validação formal com dataset anotado (--data)
    if args.data:
        executar_validacao_supervisionada(
            model=model,
            data_path=args.data,
            conf_thresh=args.conf,
            iou_thresh=args.iou,
            device=args.device
        )

    # 3. Se nenhuma fonte de vídeo for informada e também sem --data, definir default em 'videos_teste'
    if not args.fonte and not args.data:
        print("[INFORMAÇÃO] Nenhuma fonte informada. Buscando vídeos padrão na pasta 'videos_teste'...")
        args.fonte = "videos_teste"

    # 4. Avaliação em arquivos de vídeo
    if args.fonte:
        arquivos_video = localizar_arquivos_video(args.fonte)

        if not arquivos_video:
            print(f"[ERRO] Nenhum arquivo de vídeo válido foi localizado a partir de: {args.fonte}")
            if not args.data:
                sys.exit(1)
        else:
            resultados = []
            for vid_path in arquivos_video:
                res = avaliar_video(
                    model=model,
                    video_path=vid_path,
                    conf_thresh=args.conf,
                    iou_thresh=args.iou,
                    max_frames=args.max_frames,
                    device=args.device
                )
                if res:
                    resultados.append(res)

            # Imprimir relatório no console
            imprimir_relatorio_console(resultados, model_name=model_path.name, conf_thresh=args.conf)

            # Salvar CSV se solicitado
            if args.salvar_csv is not None:
                if args.salvar_csv == "DEFAULT":
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    csv_filename = f"avaliacao_modelo_{ts}.csv"
                else:
                    csv_filename = args.salvar_csv
                    if not csv_filename.endswith(".csv"):
                        csv_filename += ".csv"

                output_path = Path(args.output_dir) / csv_filename
                salvar_resultados_csv(resultados, output_path)


if __name__ == "__main__":
    main()
