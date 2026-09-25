"""
CogniMove — Pipeline de Treinamento YOLOv8 (Dataset Unificado)

NOTA SOBRE BACKUPS:
Ao final do treinamento, o modelo de produção anterior (backend/models/best.pt)
é salvo automaticamente como backup com timestamp (ex: best.pt.bak.YYYYMMDD_HHMMSS).
Como esses backups se acumulam em backend/models/ ao longo do tempo, recomenda-se
uma limpeza periódica manual para economizar espaço em disco.
"""
import os
import sys
import shutil
import datetime
from pathlib import Path
from dotenv import load_dotenv
from ultralytics import YOLO

# Injetar truststore para certificados SSL institucionais se disponível
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

# Definição dos caminhos absolutos utilizando Path(__file__)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Carregar variáveis de ambiente se existirem
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)

# Caminhos principais baseados na raiz do projeto
BASE_MODEL_PATH = PROJECT_ROOT / "backend" / "models" / "yolov8n.pt"
DATA_YAML_PATH = PROJECT_ROOT / "backend" / "training" / "datasets" / "unificado" / "data.yaml"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "outputs" / "runs"
DEST_MODELS_DIR = PROJECT_ROOT / "backend" / "models"

def main():
    print("=" * 70)
    print("  [CogniMove] Pipeline de Treinamento YOLOv8 - Dataset Unificado")
    print("=" * 70)

    # 1. Validação e Seleção do Modelo Base
    if BASE_MODEL_PATH.exists():
        model_input = str(BASE_MODEL_PATH)
        print(f"[MODELO] Modelo base localizado em: {model_input}")
    else:
        # Fallback para download automático do yolov8n.pt
        model_input = "yolov8n.pt"
        print(f"[AVISO] Modelo base não encontrado em {BASE_MODEL_PATH}. Utilizando fallback: '{model_input}'")

    print(f"[MODELO] Inicializando YOLOv8 com '{model_input}'...")
    model = YOLO(model_input)

    # 2. Validação do arquivo data.yaml do dataset unificado
    if not DATA_YAML_PATH.exists():
        print(f"[ERRO] O arquivo de configuração {DATA_YAML_PATH} não foi encontrado!")
        print("Certifique-se de executar o script de mesclagem de datasets (merge_datasets.py) antes do treinamento.")
        sys.exit(1)

    print(f"[CONFIG] Arquivo data.yaml configurado em: {DATA_YAML_PATH}")

    # Configuração dos parâmetros de treino
    epochs = 50
    imgsz = 640
    run_name = "treino_fecart_unificado"

    # Garantir que a pasta de outputs exista
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "-" * 70)
    print("[LOG/INFO] INICIANDO O TREINAMENTO DO MODELO YOLOv8")
    print(f"  - Dataset config (data): {DATA_YAML_PATH}")
    print(f"  - Modelo base: {model_input}")
    print(f"  - Épocas: {epochs}")
    print(f"  - Tamanho da imagem (imgsz): {imgsz}")
    print(f"  - Pasta de projeto (project): {OUTPUT_DIR}")
    print(f"  - Nome do experimento (name): {run_name}")
    print("-" * 70 + "\n")

    # 3. Execução do Treinamento
    results = model.train(
        data=str(DATA_YAML_PATH),
        epochs=epochs,
        imgsz=imgsz,
        project=str(OUTPUT_DIR),
        name=run_name,
        exist_ok=True,
        workers=0,  # Compatível com Windows
        batch=8
    )

    # Exibir resumo das métricas do treinamento
    try:
        metrics = results.results_dict if hasattr(results, "results_dict") else {}
        print("\n[LOG/INFO] Métricas do treinamento:")
        for chave, valor in metrics.items():
            print(f"  - {chave}: {valor}")
    except Exception as e:
        print(f"[AVISO] Não foi possível extrair métricas detalhadas: {e}")

    # 4. Localização e salvamento dos pesos finais (best.pt)
    best_weights_source = Path(results.save_dir) / "weights" / "best.pt"
    best_weights_dest = DEST_MODELS_DIR / "best.pt"

    print("\n" + "=" * 70)
    print("[LOG/INFO] TREINAMENTO CONCLUÍDO COM SUCESSO!")
    if best_weights_source.exists():
        print(f"[LOG/INFO] Pesos finais gerados (best.pt) em: {best_weights_source}")
        
        # Fazer backup do modelo anterior antes de sobrescrever
        try:
            DEST_MODELS_DIR.mkdir(parents=True, exist_ok=True)
            if best_weights_dest.exists():
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = DEST_MODELS_DIR / f"best.pt.bak.{ts}"
                shutil.copy2(best_weights_dest, backup_path)
                print(f"[LOG/INFO] Backup do modelo anterior salvo em: {backup_path}")

            shutil.copy2(best_weights_source, best_weights_dest)
            print(f"[LOG/INFO] Pesos 'best.pt' atualizados e salvos em: {best_weights_dest}")
        except Exception as e:
            print(f"[AVISO] Não foi possível copiar 'best.pt' para {best_weights_dest}: {e}")
    else:
        print(f"[AVISO] Arquivo de pesos finais não foi encontrado no diretório de execução: {best_weights_source}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()


