import os
import sys
from dotenv import load_dotenv
from roboflow import Roboflow
from ultralytics import YOLO

# Carrega as variáveis do arquivo .env (forçando o override caso já exista no terminal)
load_dotenv(override=True)

def main():
    # 1. Definir o caminho esperado para o data.yaml do novo dataset
    dataset_dir = "Imagens-Cognimove-1"
    data_yaml_path = os.path.abspath(os.path.join(dataset_dir, "data.yaml"))
    
    # 2. Se o dataset não estiver na pasta local, tenta baixá-lo do Roboflow
    if not os.path.exists(data_yaml_path):
        print(f"O dataset '{dataset_dir}' não foi encontrado em: {data_yaml_path}")
        print("Iniciando conexão com Roboflow para tentar o download...")
        try:
            # Obtém a API Key de forma segura do arquivo .env
            api_key = os.getenv("ROBOFLOW_API_KEY")
            if api_key:
                api_key = api_key.strip()
                
            if not api_key:
                raise ValueError("Chave de API do Roboflow ausente no arquivo .env.")
                
            rf = Roboflow(api_key=api_key)
            project = rf.workspace("mell-sowg7").project("imagens-cognimove")
            dataset = project.version(1).download("yolov8")
            
            # Atualiza o caminho após o download
            dataset_dir = dataset.location
            data_yaml_path = os.path.abspath(os.path.join(dataset_dir, "data.yaml"))
            print(f"Dataset baixado com sucesso em: {dataset_dir}")
        except Exception as e:
            print("\n[Erro] Falha ao baixar o dataset automaticamente do Roboflow:")
            print(e)
            print("\n[DICA] Esse erro geralmente ocorre por conta de chave de API inválida ou falta de permissão.")
            print("Altere a 'api_key' no arquivo yolo_train.py com a sua chave privada do Roboflow e execute novamente.")
            return

    # Confirmação adicional de que o arquivo data.yaml existe
    if not os.path.exists(data_yaml_path):
        print(f"\n[Erro] O arquivo '{data_yaml_path}' não pôde ser localizado.")
        return

    print(f"\n--- Iniciando Treinamento YOLOv8 ---")
    print(f"Arquivo data.yaml configurado em: {data_yaml_path}")
    
    # 3. Carregar o modelo YOLOv8n pré-treinado
    print("Carregando o modelo YOLOv8 nano (yolov8n.pt)...")
    model = YOLO("yolov8n.pt")
    
    # 4. Iniciar o treinamento por 20 épocas
    print("Iniciando o treinamento por 20 épocas...")
    # Usando epochs=20 como solicitado. O parâmetro device será resolvido automaticamente (GPU ou CPU).
    results = model.train(data=data_yaml_path, epochs=20, imgsz=640)
    
    # 5. Confirmar o caminho de salvamento do melhor modelo treinado (best.pt)
    save_dir = results.save_dir
    best_pt_path = os.path.join(save_dir, "weights", "best.pt")
    
    print("\n=== Treinamento Concluído com Sucesso! ===")
    print(f"Caminho exato do novo modelo treinado: {os.path.abspath(best_pt_path)}")

if __name__ == "__main__":
    main()
