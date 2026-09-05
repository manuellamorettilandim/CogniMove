"""
===============================================================================
CogniMove — Script ETL de Merge e Sanitização de Datasets YOLOv8
===============================================================================
Engenharia de Dados & Visão Computacional

Este script realiza a fusão (ETL) de dois datasets no formato YOLOv8:
1. Dataset Local (Sintético / Augmentado) -> Prefixo 'sintetico_'
2. Dataset Roboflow (Anotado Cloud)      -> Prefixo 'robo_'

Regras de Negócio e Sanitização de Classes:
- Filtra estritamente a classe de índice 10 do dataset Roboflow.
- Remapeia a classe 10 do Roboflow para o índice 1 no dataset unificado.
- Descarte total das classes 0 a 9 do dataset Roboflow.
- Preserva integralmente as anotações do dataset local (apenas aplicando renomeação).
- Estrutura final de destino no padrão YOLOv8:
    backend/training/datasets/unificado/
    ├── images/
    │   ├── train/
    │   └── val/
    └── labels/
        ├── train/
        └── val/
===============================================================================
"""

import os
import sys
import shutil
import logging
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# =============================================================================
# ⚙️ CONFIGURAÇÃO DE CAMINHOS COM PATHLIB (RAIZ DO PROJETO)
# =============================================================================
# 1. Caminho absoluto do script atual (backend/training/merge_datasets.py)
SCRIPT_DIR = Path(__file__).resolve().parent



# 2. Caminho absoluto da RAIZ do projeto CogniMove (dois níveis acima)
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# 3. Resolução dinâmica dos diretórios de origem e destino usando caminhos absolutos
LOCAL_CANDIDATES = [
    PROJECT_ROOT / "backend" / "training" / "datasets" / "temp_local",
    PROJECT_ROOT / "datasets" / "temp_local",
    SCRIPT_DIR / "datasets" / "temp_local",
    SCRIPT_DIR / "datasets" / "dataset_limite",
    PROJECT_ROOT / "backend" / "training" / "datasets" / "dataset_limite",
]

ROBOFLOW_CANDIDATES = [
    PROJECT_ROOT / "backend" / "training" / "datasets" / "temp_roboflow",
    PROJECT_ROOT / "datasets" / "temp_roboflow",
    SCRIPT_DIR / "datasets" / "temp_roboflow",
    SCRIPT_DIR / "datasets" / "Imagens-Cognimove-1",
]

def find_best_directory(candidates: list[Path]) -> Path:
    """Retorna o primeiro diretório existente da lista de candidatos, ou o padrão se nenhum existir."""
    for path in candidates:
        if path.exists() and path.is_dir():
            return path
    return candidates[0]

# Definição dos caminhos finais absolutos
DATASET_LOCAL_DIR = find_best_directory(LOCAL_CANDIDATES)
DATASET_ROBOFLOW_DIR = find_best_directory(ROBOFLOW_CANDIDATES)
DATASET_UNIFICADO_DIR = PROJECT_ROOT / "backend" / "training" / "datasets" / "unificado"

# Configurações de Prefixo
PREFIX_LOCAL = "sintetico_"
PREFIX_ROBOFLOW = "robo_"

# Configurações do Filtro de Classes (Roboflow)
ROBOFLOW_SOURCE_CLASS_ID = "10"  # Classe a ser filtrada (origem)
ROBOFLOW_TARGET_CLASS_ID = "1"   # Novo índice atribuído (destino)

# Extensões suportadas de imagem
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# =============================================================================
# 🛠️ FUNÇÕES AUXILIARES DE ETL
# =============================================================================

def resolve_split_dirs(dataset_dir: Path, split_name: str):
    aliases = [split_name]
    if split_name in ("val", "valid"):
        aliases = ["val", "valid"]

    for alias in aliases:
        img_dir = dataset_dir / "images" / alias
        lbl_dir = dataset_dir / "labels" / alias
        if img_dir.exists() and lbl_dir.exists():
            return img_dir, lbl_dir

    for alias in aliases:
        img_dir = dataset_dir / alias / "images"
        lbl_dir = dataset_dir / alias / "labels"
        if img_dir.exists() and lbl_dir.exists():
            return img_dir, lbl_dir

    return None, None


def process_local_dataset(split_dest_name: str, dest_img_dir: Path, dest_lbl_dir: Path):
    src_img_dir, src_lbl_dir = resolve_split_dirs(DATASET_LOCAL_DIR, split_dest_name)

    if not src_img_dir or not src_img_dir.exists():
        logging.warning(f"  [Dataset Local] Split '{split_dest_name}' não encontrado em: {DATASET_LOCAL_DIR}")
        return 0, 0

    copied_images = 0
    copied_labels = 0

    for img_path in src_img_dir.iterdir():
        if img_path.is_file() and img_path.suffix.lower() in IMAGE_EXTENSIONS:
            new_img_name = f"{PREFIX_LOCAL}{img_path.name}"
            dest_img_path = dest_img_dir / new_img_name
            
            try:
                shutil.copy2(img_path, dest_img_path)
                copied_images += 1
            except OSError as e:
                logging.warning(f"  ⚠️ Não foi possível copiar '{img_path.name}' (Arquivo no OneDrive não baixado): {e}")
                continue

            # Copiar rótulo correspondente
            lbl_filename = f"{img_path.stem}.txt"
            src_lbl_path = src_lbl_dir / lbl_filename
            new_lbl_name = f"{PREFIX_LOCAL}{lbl_filename}"
            dest_lbl_path = dest_lbl_dir / new_lbl_name

            if src_lbl_path.exists():
                try:
                    shutil.copy2(src_lbl_path, dest_lbl_path)
                    copied_labels += 1
                except OSError:
                    dest_lbl_path.touch()
            else:
                dest_lbl_path.touch()

    return copied_images, copied_labels


def process_roboflow_dataset(split_dest_name: str, dest_img_dir: Path, dest_lbl_dir: Path):
    src_img_dir, src_lbl_dir = resolve_split_dirs(DATASET_ROBOFLOW_DIR, split_dest_name)

    if not src_img_dir or not src_img_dir.exists():
        logging.warning(f"  [Roboflow] Split '{split_dest_name}' não encontrado em: {DATASET_ROBOFLOW_DIR}")
        return 0, 0, 0

    copied_images = 0
    copied_labels = 0
    total_annotations_kept = 0

    for img_path in src_img_dir.iterdir():
        if img_path.is_file() and img_path.suffix.lower() in IMAGE_EXTENSIONS:
            new_img_name = f"{PREFIX_ROBOFLOW}{img_path.name}"
            dest_img_path = dest_img_dir / new_img_name

            try:
                shutil.copy2(img_path, dest_img_path)
                copied_images += 1
            except OSError as e:
                logging.warning(f"  ⚠️ Não foi possível copiar '{img_path.name}' (Arquivo no OneDrive não baixado): {e}")
                continue

            lbl_filename = f"{img_path.stem}.txt"
            src_lbl_path = src_lbl_dir / lbl_filename
            new_lbl_name = f"{PREFIX_ROBOFLOW}{lbl_filename}"
            dest_lbl_path = dest_lbl_dir / new_lbl_name

            filtered_lines = []

            if src_lbl_path.exists():
                try:
                    with open(src_lbl_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line_clean = line.strip()
                            if not line_clean:
                                continue

                            parts = line_clean.split()
                            class_id = parts[0]

                            if class_id == ROBOFLOW_SOURCE_CLASS_ID:
                                parts[0] = ROBOFLOW_TARGET_CLASS_ID
                                filtered_lines.append(" ".join(parts) + "\n")
                                total_annotations_kept += 1
                except OSError as e:
                    logging.warning(f"  ⚠️ Erro ao ler rótulo '{lbl_filename}': {e}")

            with open(dest_lbl_path, "w", encoding="utf-8") as f:
                f.writelines(filtered_lines)

            copied_labels += 1

    return copied_images, copied_labels, total_annotations_kept


# =============================================================================
# 🚀 EXECUÇÃO PRINCIPAL DO PIPELINE ETL
# =============================================================================

def main():
    print("=================================================================")
    print(" [ETL] CogniMove -- Pipeline de Merge de Datasets YOLOv8")
    print("=================================================================")
    print(f"  Raiz do Projeto: {PROJECT_ROOT}")
    print(f"  Origem Local   : {DATASET_LOCAL_DIR}")
    print(f"  Origem Roboflow: {DATASET_ROBOFLOW_DIR}")
    print(f"  Destino        : {DATASET_UNIFICADO_DIR}")
    print("-----------------------------------------------------------------")

    # VERIFICAÇÃO DE PRÉ-VOO: Checa a existência dos diretórios de origem
    if not DATASET_LOCAL_DIR.exists():
        logging.warning(
            f"⚠️ Diretório do Dataset Local NÃO foi encontrado:\n   -> {DATASET_LOCAL_DIR}\n"
            f"   (Crie a pasta 'temp_local' em '{SCRIPT_DIR / 'datasets'}' ou ajuste o caminho)."
        )
    else:
        logging.info(f"✅ Diretório Local encontrado em: {DATASET_LOCAL_DIR}")

    if not DATASET_ROBOFLOW_DIR.exists():
        logging.warning(
            f"⚠️ Diretório do Dataset Roboflow NÃO foi encontrado:\n   -> {DATASET_ROBOFLOW_DIR}\n"
            f"   (Crie a pasta 'temp_roboflow' em '{SCRIPT_DIR / 'datasets'}' ou ajuste o caminho)."
        )
    else:
        logging.info(f"✅ Diretório Roboflow encontrado em: {DATASET_ROBOFLOW_DIR}")

    print("-----------------------------------------------------------------")

    # Garante a criação da estrutura de destino unificada
    splits = ["train", "val"]
    for split in splits:
        (DATASET_UNIFICADO_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (DATASET_UNIFICADO_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    summary = {}

    for split in splits:
        print(f"\n[SPLIT] Processando split: '{split}'...")

        dest_img_dir = DATASET_UNIFICADO_DIR / "images" / split
        dest_lbl_dir = DATASET_UNIFICADO_DIR / "labels" / split

        # 1. Processar Dataset Local
        loc_imgs, loc_lbls = process_local_dataset(split, dest_img_dir, dest_lbl_dir)
        print(f"  [Dataset Local] Imagens copiadas: {loc_imgs} | Rótulos copiados: {loc_lbls}")

        # 2. Processar Dataset Roboflow
        rf_imgs, rf_lbls, rf_annos = process_roboflow_dataset(split, dest_img_dir, dest_lbl_dir)
        print(f"  [Roboflow] Imagens copiadas: {rf_imgs} | Rótulos processados: {rf_lbls} | Anotações mantidas (Classe 10 -> 1): {rf_annos}")

        summary[split] = {
            "total_images": loc_imgs + rf_imgs,
            "total_labels": loc_lbls + rf_lbls,
            "roboflow_annotations": rf_annos
        }

    print("\n=================================================================")
    print(" [OK] ETL Concluído com Sucesso!")
    print("=================================================================")
    print(f" Diretório Unificado Gerado: {DATASET_UNIFICADO_DIR}")
    for split, stats in summary.items():
        print(f"   * Split '{split}': {stats['total_images']} imagens | {stats['total_labels']} rótulos")
    print("=================================================================")


if __name__ == "__main__":
    main()



