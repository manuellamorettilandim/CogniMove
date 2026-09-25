import os
import sys
import subprocess
import glob
from dotenv import load_dotenv

# Função para garantir que os pacotes necessários estão instalados
def install_package(package):
    try:
        __import__(package)
    except ImportError:
        print(f"Biblioteca '{package}' não encontrada. Instalando...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Garante que roboflow, ultralytics e python-dotenv estão instalados
install_package("roboflow")
install_package("ultralytics")
install_package("python-dotenv")

# Carrega as variáveis do arquivo .env (forçando o override caso já exista no terminal)
load_dotenv(override=True)

# Agora podemos importar
from roboflow import Roboflow
from ultralytics import YOLO

def main():
    # 1. Download do dataset do Roboflow
    print("Iniciando conexão com Roboflow...")
    try:
        # Carrega a api_key de forma segura
        api_key = os.getenv("ROBOFLOW_API_KEY")
        if not api_key:
            raise ValueError(
                "Chave de API do Roboflow ausente. Defina ROBOFLOW_API_KEY no arquivo .env "
                "(veja .env.example)."
            )
            
        rf = Roboflow(api_key=api_key)
        project = rf.workspace("mell-sowg7").project("imagens-cognimove")
        
        print("Baixando o dataset no formato yolov8...")
        dataset = project.version(1).download("yolov8")
        
        # O dataset.location nos dá o caminho absoluto onde o dataset foi salvo
        dataset_path = dataset.location
        print(f"Dataset baixado com sucesso em: {dataset_path}")
        
        # O arquivo data.yaml localiza-se na raiz do dataset baixado
        data_yaml_path = os.path.join(dataset_path, "data.yaml")
        print(f"Arquivo de configuração data.yaml localizado em: {data_yaml_path}")
    except Exception as e:
        print("\n[Erro] Falha ao conectar ao Roboflow ou baixar o dataset:")
        print(e)
        print("\n[DICA] Esse erro geralmente ocorre por problemas de permissão ou chave de API incorreta.")
        print("Se o projeto 'Imagens-Cognimove' no workspace 'mell-sowg7' for privado, você precisa")
        print("definir 'ROBOFLOW_API_KEY' no seu arquivo .env com a sua chave privada do Roboflow (disponível em suas configurações do Roboflow).")
        return
    
    # 2. Localizar imagens de teste
    test_images_dir = os.path.join(dataset_path, "test", "images")
    
    # Extensões comuns de imagem
    image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
    image_paths = []
    for ext in image_extensions:
        image_paths.extend(glob.glob(os.path.join(test_images_dir, ext)))
        image_paths.extend(glob.glob(os.path.join(test_images_dir, ext.upper())))
    
    if not image_paths:
        print(f"Aviso: Nenhuma imagem encontrada no diretório {test_images_dir}")
        return
    
    print(f"Total de imagens de teste encontradas: {len(image_paths)}")
    
    # Selecionar algumas imagens de teste para predição (ex: até 5 imagens)
    sample_images = image_paths[:5]
    print(f"Selecionando {len(sample_images)} imagens de teste para inferência...")
    
    # 3. Carregar o modelo YOLOv8n
    print("Carregando o modelo YOLOv8n...")
    model = YOLO("yolov8n.pt")
    
    # 4. Fazer o predict nas imagens selecionadas
    print("Executando a predição...")
    # save=True salvará os resultados na pasta runs/detect/predict/
    results = model.predict(source=sample_images, save=True, conf=0.25)
    
    print("\n--- Resultados das Predições ---")
    for r in results:
        # Exibe o caminho do arquivo original e os resultados das detecções
        path = r.path
        boxes = r.boxes
        print(f"\nImagem: {os.path.basename(path)}")
        if len(boxes) == 0:
            print("  Nenhum objeto detectado.")
        else:
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                conf = float(box.conf[0])
                print(f"  Classe detectada: {cls_name} (Confiança: {conf:.2f})")
                
    print("\nPredições concluídas! As imagens anotadas foram salvas na pasta 'runs/detect/predict'.")
    print(f"Para treinamento, o arquivo de configuração de dados está em: {data_yaml_path}")
    
    # --- EXEMPLO DE TREINAMENTO (Opcional) ---
    # Se você quiser iniciar o treinamento usando este dataset, descomente a linha abaixo:
    # print("\n[Dica] Iniciando o treinamento...")
    # model.train(data=data_yaml_path, epochs=50, imgsz=640, device=0)

if __name__ == "__main__":
    main()
