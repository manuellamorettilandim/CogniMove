import os
import sys
import glob
import random
import cv2
import numpy as np

def create_dataset_directories(base_dir):
    """Cria a estrutura de diretórios padrão YOLOv8."""
    for split in ["train", "valid", "test"]:
        os.makedirs(os.path.join(base_dir, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, split, "labels"), exist_ok=True)

# ATENÇÃO: Os arquivos de configuração de dataset (em backend/training/configs/ ou
# na raiz do módulo de treinamento) devem sempre ser gerados de forma programática
# por este script utilizando caminhos relativos, nunca editados manualmente com
# caminhos absolutos locais específicos de uma máquina ou usuário.
def generate_yaml(dataset_dir, yaml_path):
    """Gera o arquivo de configuração data_limite.yaml com caminhos relativos."""
    yaml_content = """# Configuração do Dataset CogniMove - Classe Limite
train: dataset_limite/train/images
val: dataset_limite/valid/images
test: dataset_limite/test/images

# Classes
names:
  0: Limite
  1: Faixa_Pedestre
  2: Semaforo

nc: 3
"""
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)
    print(f"[Dataset] data.yaml salvo em: {yaml_path}")

def augment_image_and_boxes(img, boxes):
    """Aplica aumentos de dados (brilho, contraste, ruído, saturação) mantendo as caixas válidas."""
    h, w = img.shape[:2]
    aug_img = img.copy().astype(np.float32)
    
    # Variação de brilho e contraste
    alpha = random.uniform(0.7, 1.3) # Contraste
    beta = random.uniform(-30, 30)    # Brilho
    aug_img = np.clip(aug_img * alpha + beta, 0, 255).astype(np.uint8)
    
    # Ruído gaussiano ocasional (simula chuva/noite/granulação de câmera)
    if random.random() > 0.5:
        noise = np.random.normal(0, 8, img.shape).astype(np.float32)
        aug_img = np.clip(aug_img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        
    # Desfoque leve ocasional
    if random.random() > 0.6:
        ksize = random.choice([3, 5])
        aug_img = cv2.GaussianBlur(aug_img, (ksize, ksize), 0)

    # Inversão horizontal ocasional
    new_boxes = []
    if random.random() > 0.5:
        aug_img = cv2.flip(aug_img, 1)
        for cls_id, cx, cy, bw, bh in boxes:
            new_cx = 1.0 - cx
            new_boxes.append((cls_id, new_cx, cy, bw, bh))
    else:
        new_boxes = boxes[:]

    return aug_img, new_boxes

def generate_training_data():
    """Extrai frames dos vídeos de teste e gera anotações precisas para a classe Limite."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.dirname(base_dir)
    dataset_dir = os.path.join(base_dir, "dataset_limite")
    create_dataset_directories(dataset_dir)
    
    # 1. Definição das marcações de referência da classe Limite por vídeo
    # Formato das caixas normalizadas [cls_id, x_center, y_center, width, height]
    # cls 0 = Limite, cls 1 = Faixa_Pedestre, cls 2 = Semaforo
    video_configs = {
        "video_teste4.mp4": {
            "resolucao_esperada": (352, 240),  # (largura, altura)
            "boxes": [
                # Limite inferior (linha de retenção antes da área de bicicletas / bike box)
                (0, (20 + 145)/2/352, (140 + 220)/2/240, (145 - 20)/352, (220 - 140)/240),
                # Limite superior (linha de retenção de ciclistas antes da faixa de pedestres)
                (0, (75 + 185)/2/352, (100 + 175)/2/240, (185 - 75)/352, (175 - 100)/240),
                # Limite da pista direita
                (0, (275 + 325)/2/352, (150 + 170)/2/240, (325 - 275)/352, (170 - 150)/240),
                # Faixa de pedestres direita
                (1, (270 + 350)/2/352, (180 + 240)/2/240, (350 - 270)/352, (240 - 180)/240),
                # Semáforo direito
                (2, 335/352, 130/240, 20/352, 35/240)
            ]
        },
        "video_teste3.mp4": {
            "resolucao_esperada": (480, 270),
            "boxes": [
                # Limite da pista esquerda (antes da faixa de pedestres)
                (0, (30 + 180)/2/480, (195 + 220)/2/270, (180 - 30)/480, (220 - 195)/270),
                # Limite da pista direita
                (0, (260 + 380)/2/480, (180 + 205)/2/270, (380 - 260)/480, (205 - 180)/270),
                # Faixa de pedestres esquerda
                (1, (30 + 180)/2/480, (160 + 205)/2/270, (180 - 30)/480, (205 - 160)/270),
                # Faixa de pedestres direita
                (1, (260 + 380)/2/480, (150 + 185)/2/270, (380 - 260)/480, (185 - 150)/270),
                # Semáforos
                (2, 130/480, 75/270, 25/480, 40/270),
                (2, 385/480, 75/270, 25/480, 40/270)
            ]
        },
        "video_teste2.mp4": {
            "resolucao_esperada": (898, 506),
            "boxes": [
                # Linha de limite / retenção
                (0, (480 + 580)/2/898, (180 + 230)/2/506, (580 - 480)/898, (230 - 180)/506),
                # Faixa de pedestres
                (1, (400 + 580)/2/898, (220 + 340)/2/506, (580 - 400)/898, (340 - 220)/506)
            ]
        },
        "video_teste.mp4": {
            "resolucao_esperada": (None, None),  # já usa proporção relativa fixa, não depende da resolução exata
            "boxes": [
                # Limite de pista
                (0, 0.5, 0.7, 0.35, 0.08)
            ]
        }
    }

    all_samples = []
    
    # Extrair frames variados de cada vídeo
    for vname, cfg in video_configs.items():
        candidates = [
            os.path.join(workspace_dir, "videos_originais", vname),
            os.path.join(base_dir, vname)
        ]
        vpath = next((p for p in candidates if os.path.exists(p)), None)
        if not vpath:
            continue
            
        cap = cv2.VideoCapture(vpath)
        largura_real = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        altura_real = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        largura_esperada, altura_esperada = cfg.get("resolucao_esperada", (None, None))

        if largura_esperada and (largura_real != largura_esperada or altura_real != altura_esperada):
            print(
                f"[AVISO] '{vname}' tem resolução {largura_real}x{altura_real}, "
                f"mas as anotações foram calculadas para {largura_esperada}x{altura_esperada}. "
                f"Pulando este vídeo para não gerar anotações incorretas."
            )
            cap.release()
            continue

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            continue
            
        # Coletar até 25 frames espaçados ao longo do vídeo
        step = max(1, total_frames // 25)
        for f_idx in range(0, min(total_frames, 25 * step), step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret:
                continue
            
            clean_name = os.path.splitext(vname)[0]
            sample_id = f"{clean_name}_f{f_idx:05d}"
            all_samples.append((sample_id, frame, cfg["boxes"]))
            
            # Gerar versões com aumentações de dados
            for aug_i in range(3):
                aug_frame, aug_boxes = augment_image_and_boxes(frame, cfg["boxes"])
                all_samples.append((f"{sample_id}_aug{aug_i}", aug_frame, aug_boxes))
                
        cap.release()

    print(f"[Dataset] Total de amostras geradas: {len(all_samples)}")
    random.seed(42)
    random.shuffle(all_samples)

    # Dividir em Train (70%), Valid (20%), Test (10%)
    n = len(all_samples)
    train_end = int(n * 0.7)
    val_end = int(n * 0.9)

    splits = {
        "train": all_samples[:train_end],
        "valid": all_samples[train_end:val_end],
        "test": all_samples[val_end:]
    }

    for split_name, samples in splits.items():
        for sample_id, frame, boxes in samples:
            img_file = os.path.join(dataset_dir, split_name, "images", f"{sample_id}.jpg")
            lbl_file = os.path.join(dataset_dir, split_name, "labels", f"{sample_id}.txt")
            
            # Salvamento seguro de imagem compatível com caminhos UTF-8 no Windows
            _, buffer = cv2.imencode(".jpg", frame)
            with open(img_file, "wb") as f:
                f.write(buffer)
                
            with open(lbl_file, "w", encoding="utf-8") as f:
                for cls_id, cx, cy, bw, bh in boxes:
                    f.write(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

    yaml_path = os.path.join(base_dir, "data_limite.yaml")
    generate_yaml(dataset_dir, yaml_path)
    
    print("\n=== Dataset da Classe 'Limite' Gerado com Sucesso! ===")
    print(f"Treino: {len(splits['train'])} imagens")
    print(f"Validação: {len(splits['valid'])} imagens")
    print(f"Teste: {len(splits['test'])} imagens")
    print(f"Arquivo YAML: {yaml_path}")

if __name__ == "__main__":
    generate_training_data()
