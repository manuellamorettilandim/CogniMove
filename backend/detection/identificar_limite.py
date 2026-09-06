import os
import sys
import glob
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO

# Garantir imports relativos de utils_video
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
_ROOT = _BACKEND.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from utils_video import resolver_fonte_video, PASTAS_VIDEO, EXTENSOES_VIDEO

# Coordenadas calibradas de referência para câmeras fixas conhecidas
CAMERA_PRESETS = {
    "caetano_alvares": {
        "keywords": ["video_teste4", "caetano", "casa_verde", "0069"],
        "lines": [
            # Linha de limite veicular (atrás do bike box): (x1, y1) -> (x2, y2)
            {"name": "Limite Veicular", "pt1": (20, 150), "pt2": (145, 220), "color": (0, 255, 255)},
            # Linha de limite ciclistas (antes da faixa): (x1, y1) -> (x2, y2)
            {"name": "Limite Ciclista", "pt1": (75, 105), "pt2": (185, 172), "color": (255, 255, 0)},
            # Linha de retenção pista direita
            {"name": "Limite Faixa Direita", "pt1": (275, 150), "pt2": (330, 168), "color": (0, 255, 255)}
        ],
        "polygon": np.array([[20, 145], [145, 220], [185, 170], [75, 100]], np.int32)
    },
    "maria_paula": {
        "keywords": ["video_teste3", "maria_paula", "santo_amaro", "0628"],
        "lines": [
            {"name": "Limite Pista Esquerda", "pt1": (30, 205), "pt2": (180, 205), "color": (0, 255, 255)},
            {"name": "Limite Pista Direita", "pt1": (260, 190), "pt2": (380, 190), "color": (0, 255, 255)}
        ],
        "polygon": None
    },
    "general": {
        "keywords": [],
        "lines": [
            {"name": "Limite Geral", "pt1": (0.1, 0.7), "pt2": (0.9, 0.7), "color": (0, 255, 255)}
        ],
        "polygon": None
    }
}

def detect_preset_for_video(video_path, width, height):
    """Identifica automaticamente a calibração adequada com base no nome do arquivo ou dimensões."""
    basename = os.path.basename(video_path).lower()
    for key, preset in CAMERA_PRESETS.items():
        for kw in preset.get("keywords", []):
            if kw in basename:
                # Escalar para a resolução atual do vídeo
                scaled_lines = []
                # Determinar resolução base
                ref_w, ref_h = (352, 240) if key == "caetano_alvares" else (480, 270)
                scale_x = width / ref_w
                scale_y = height / ref_h
                
                for line in preset["lines"]:
                    p1 = (int(line["pt1"][0] * scale_x), int(line["pt1"][1] * scale_y))
                    p2 = (int(line["pt2"][0] * scale_x), int(line["pt2"][1] * scale_y))
                    scaled_lines.append({
                        "name": line["name"],
                        "pt1": p1,
                        "pt2": p2,
                        "color": line["color"]
                    })
                
                scaled_poly = None
                if preset.get("polygon") is not None:
                    scaled_poly = (preset["polygon"] * [scale_x, scale_y]).astype(np.int32)
                    
                return key, scaled_lines, scaled_poly
                
    # Preset padrão normalizado
    default_lines = [
        {
            "name": "Limite",
            "pt1": (int(width * 0.1), int(height * 0.75)),
            "pt2": (int(width * 0.9), int(height * 0.75)),
            "color": (0, 255, 255)
        }
    ]
    return "general", default_lines, None

def check_line_intersection(p1, p2, p3, p4):
    """Verifica se o segmento p1-p2 intercepta o segmento p3-p4."""
    def ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

def point_to_line_distance(pt, line_pt1, line_pt2):
    """Calcula a distância mínima de um ponto a um segmento de reta."""
    p = np.array(pt, dtype=np.float32)
    a = np.array(line_pt1, dtype=np.float32)
    b = np.array(line_pt2, dtype=np.float32)
    
    ab = b - a
    ab_len_sq = np.dot(ab, ab)
    if ab_len_sq == 0:
        return np.linalg.norm(p - a)
        
    t = max(0, min(1, np.dot(p - a, ab) / ab_len_sq))
    projection = a + t * ab
    return np.linalg.norm(p - projection)

def resolve_video_path(video_path):
    """Localiza o arquivo de vídeo utilizando resolver_fonte_video centralizado."""
    if not video_path:
        return None
    resolved = resolver_fonte_video(video_path, root=_ROOT)
    if isinstance(resolved, str) and os.path.exists(resolved) and os.path.isfile(resolved) and os.path.getsize(resolved) > 0:
        return os.path.abspath(resolved)
    return None

def processar_video(video_path, model_path="best.pt", output_path=None):
    """Processa um vídeo identificando a classe Limite e monitorando invasões."""
    resolved_video = resolve_video_path(video_path)
    if not resolved_video:
        print(f"[Erro] Arquivo de vídeo não encontrado: {video_path}")
        return None
    video_path = resolved_video
        
    print(f"\n=== Iniciando Processamento de Vídeo: {os.path.basename(video_path)} ===")
    
    # Carregar modelo treinado e modelo base YOLOv8 para veículos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Modelos ficam em backend/models/
    models_dir = os.path.abspath(os.path.join(script_dir, "..", "models"))
    
    if not os.path.isabs(model_path):
        best_pt = os.path.join(models_dir, model_path)
    else:
        best_pt = model_path
    
    if os.path.exists(best_pt):
        print(f"[IA] Carregando modelo customizado: {best_pt}")
        model_limite = YOLO(best_pt)
    else:
        print("[Aviso] Modelo 'best.pt' não encontrado, usando modelo base YOLOv8...")
        model_limite = None
        
    yolov8_path = os.path.join(models_dir, "yolov8n.pt")
    model_yolo = YOLO(yolov8_path if os.path.exists(yolov8_path) else "yolov8n.pt")
    
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    preset_name, lines, polygon = detect_preset_for_video(video_path, width, height)
    print(f"[Calibração] Modo de cena detectado: {preset_name} ({len(lines)} linhas de Limite configuradas)")
    
    if output_path is None:
        outputs_dir = os.path.abspath(os.path.join(script_dir, "..", "outputs", "runs", "limite_output"))
        os.makedirs(outputs_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(outputs_dir, f"{base_name}_limite_reconhecido.mp4")
        
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Classes COCO de interesse para veículos: 2: car, 3: motorcycle, 5: bus, 7: truck, 1: bicycle, 0: person
    VEHICLE_CLASSES = [1, 2, 3, 5, 7]
    
    frame_idx = 0
    total_invasions = 0
    unique_vehicles = set()
    
    print(f"[Processamento] Analisando frames ({total_frames} frames no total)...")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_idx += 1
        overlay = frame.copy()
        
        # 1. Desenhar a demarcação visual da Faixa Limite
        if polygon is not None:
            # Preenchimento translúcido da área de bike box / limite
            cv2.fillPoly(overlay, [polygon], (255, 200, 0))
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
            
        for line in lines:
            pt1 = line["pt1"]
            pt2 = line["pt2"]
            color = line["color"]
            label = line["name"]
            
            # Linha principal espessa
            cv2.line(frame, pt1, pt2, (0, 0, 0), 5) # Borda preta
            cv2.line(frame, pt1, pt2, color, 3)     # Linha colorida
            
            # Texto da marcação
            mid_x = (pt1[0] + pt2[0]) // 2
            mid_y = (pt1[1] + pt2[1]) // 2 - 8
            
            (tw, th), _ = cv2.getTextSize(f"[ {label} ]", cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (mid_x - 4, mid_y - th - 4), (mid_x + tw + 4, mid_y + 4), (0, 0, 0), -1)
            cv2.putText(frame, f"[ {label} ]", (mid_x, mid_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

        # 2. Detecção com Modelo YOLO de Veículos
        res_vehicles = model_yolo.predict(frame, classes=VEHICLE_CLASSES, conf=0.25, verbose=False)
        
        frame_invasions = 0
        if res_vehicles and len(res_vehicles) > 0:
            boxes = res_vehicles[0].boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cls_id = int(box.cls[0])
                cls_name = model_yolo.names[cls_id]
                conf = float(box.conf[0])
                
                # Ponto inferior central do veículo (área de contato com o solo)
                bottom_pt = ((x1 + x2) // 2, y2)
                
                # Verificar se o veículo tocou ou cruzou a linha de Limite
                invaded = False
                for line in lines:
                    dist = point_to_line_distance(bottom_pt, line["pt1"], line["pt2"])
                    # Se estiver dentro de 15 pixels da linha de limite
                    if dist < 18:
                        invaded = True
                        break
                        
                if invaded:
                    frame_invasions += 1
                    total_invasions += 1
                    box_color = (0, 0, 255) # Vermelho
                    status_text = f"{cls_name} - INVASAO LIMITE"
                else:
                    box_color = (0, 255, 0) # Verde
                    status_text = f"{cls_name} {conf:.2f}"
                    
                # Desenhar caixa do veículo
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                (tw, th), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), box_color, -1)
                cv2.putText(frame, status_text, (x1 + 2, y1 - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

        # 3. HUD e Painel Informativo na Tela
        cv2.rectangle(frame, (10, 10), (280, 65), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (280, 65), (0, 255, 255), 1)
        cv2.putText(frame, "COGNIMOVE - SISTEMA DE MONITORAMENTO", (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Faixa Monitorada: LIMITE (Retencao)", (15, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
        status_color = (0, 0, 255) if frame_invasions > 0 else (0, 255, 0)
        status_msg = f"Alertas de Invasao: {frame_invasions}" if frame_invasions > 0 else "Fluxo Regular (Limite Respeitado)"
        cv2.putText(frame, status_msg, (15, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.38, status_color, 1, cv2.LINE_AA)

        out.write(frame)
        
        # Limitar a análise inicial caso o vídeo seja muito longo para resposta ágil
        if frame_idx >= 300: # Primeiros 300 frames (~10 a 60 segundos de vídeo)
            break

    cap.release()
    out.release()
    
    print("\n=== Identificação de Limite Concluída! ===")
    print(f"Vídeo processado salvo em: {os.path.abspath(output_path)}")
    return output_path

if __name__ == "__main__":
    # Se passado argumento pela linha de comando
    if len(sys.argv) > 1:
        video_arg = sys.argv[1]
    else:
        # Padrão: buscar nos diretórios de vídeo do projeto
        cands = ["video_teste4.mp4", "video_teste3.mp4", "video_teste.mp4"]
        video_arg = None
        for c in cands:
            res = resolver_fonte_video(c, root=_ROOT)
            if isinstance(res, str) and os.path.exists(res):
                video_arg = res
                break
        
    if video_arg:
        processar_video(video_arg)
    else:
        print("[Erro] Nenhum vídeo encontrado para processamento.")
