import os
import glob
import sys
import argparse
from ultralytics import YOLO

def find_best_pt():
    """
    Localiza o arquivo de pesos 'best.pt' mais recente no diretório do script,
    no diretório atual de trabalho ou nas pastas de treinamento 'runs/detect/train*/weights/'.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    
    candidates = [
        os.path.join(cwd, "best.pt"),
        os.path.join(script_dir, "best.pt"),
    ]
    
    # Procurar nas pastas de treinamento runs/detect/train*/weights/
    for base in [cwd, script_dir]:
        runs_pattern = os.path.join(base, "runs", "detect", "train*", "weights", "best.pt")
        candidates.extend(glob.glob(runs_pattern))
        
    valid_candidates = [f for f in set(candidates) if os.path.isfile(f) and os.path.getsize(f) > 0]
    
    if not valid_candidates:
        raise FileNotFoundError(
            "Não foi possível encontrar o arquivo de pesos 'best.pt' no diretório atual ou nas pastas 'runs/'. "
            "Certifique-se de que o modelo treinado está no diretório correto."
        )
    
    # Retorna o arquivo modificado mais recentemente
    valid_candidates.sort(key=os.path.getmtime, reverse=True)
    return os.path.abspath(valid_candidates[0])

def find_video_file():
    """
    Localiza automaticamente um arquivo de vídeo de teste nos diretórios padrão.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    workspace_dir = os.path.dirname(script_dir)
    
    search_dirs = [cwd, script_dir, workspace_dir]
    videos_originais_dir = os.path.join(workspace_dir, "videos_originais")
    if os.path.exists(videos_originais_dir):
        search_dirs.append(videos_originais_dir)
        
    video_extensions = ["*.mp4", "*.avi", "*.mov", "*.mkv"]
    video_files = []
    
    for d in search_dirs:
        for ext in video_extensions:
            video_files.extend(glob.glob(os.path.join(d, ext)))
            video_files.extend(glob.glob(os.path.join(d, ext.upper())))
            
    valid_videos = [f for f in set(video_files) if os.path.isfile(f) and os.path.getsize(f) > 0]
    
    if not valid_videos:
        return None
        
    # Ordena pelo mais recentemente modificado
    valid_videos.sort(key=os.path.getmtime, reverse=True)
    return os.path.abspath(valid_videos[0])

def main():
    parser = argparse.ArgumentParser(description="Teste de inferência em vídeo com YOLOv8")
    parser.add_argument("video", nargs="?", help="Caminho do arquivo de vídeo de teste")
    parser.add_argument("opcao", nargs="?", choices=["1", "2"], help="Opção do modelo: 1 (best.pt) ou 2 (yolov8n.pt)")
    args = parser.parse_args()

    print("=== Inicializando Teste de Vídeo com YOLOv8 ===")
    
    # 1. Definir opção do modelo
    opcao = args.opcao
    if not opcao:
        print("Escolha o modelo de detecção:")
        print("1 - Seu modelo personalizado (best.pt - Placas e Faixas)")
        print("2 - Modelo padrão YOLOv8 (yolov8n.pt - Carros, Pessoas, Motos, Semáforos, etc.)")
        
        if sys.stdin.isatty():
            try:
                opcao = input("Digite a opção (1 ou 2) [Padrão: 1]: ").strip()
                if not opcao:
                    opcao = "1"
            except Exception:
                opcao = "1"
        else:
            print("Ambiente não-interativo detectado. Usando opção padrão: 1")
            opcao = "1"

    # 2. Localizar pesos do modelo
    if opcao == "2":
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_yolo = os.path.join(script_dir, "yolov8n.pt")
        model_path = local_yolo if os.path.exists(local_yolo) else "yolov8n.pt"
        print("\n[Modelo] Usando modelo padrão YOLOv8n (COCO)...")
    else:
        try:
            model_path = find_best_pt()
            print(f"\n[Modelo] Pesos personalizados localizados em: {model_path}")
        except FileNotFoundError as e:
            print(f"\n[Erro] {e}")
            return

    # 3. Localizar arquivo de vídeo
    video_path = args.video
    if video_path:
        if not os.path.exists(video_path):
            print(f"[Erro] O arquivo de vídeo '{video_path}' não existe.")
            return
        if not os.path.isfile(video_path):
            print(f"[Erro] O caminho '{video_path}' não é um arquivo válido.")
            return
        if os.path.getsize(video_path) == 0:
            print(f"[Erro] O arquivo de vídeo '{video_path}' está vazio (0 bytes).")
            return
        video_path = os.path.abspath(video_path)
    else:
        localizado = find_video_file()
        if localizado:
            nome_localizado = os.path.basename(localizado)
            print(f"\nVídeo localizado automaticamente: {nome_localizado}")
            
            if sys.stdin.isatty():
                try:
                    escolha = input("Aperte Enter para usar este vídeo ou digite o caminho do novo vídeo: ").strip()
                    if escolha:
                        video_path = escolha
                    else:
                        video_path = localizado
                except Exception:
                    video_path = localizado
            else:
                video_path = localizado
        else:
            print("\n[Aviso] Nenhum arquivo de vídeo (.mp4, .avi, etc.) foi encontrado automaticamente.")
            if sys.stdin.isatty():
                try:
                    video_path = input("Por favor, digite o caminho completo para o arquivo de vídeo de teste: ").strip()
                except Exception:
                    print("[Erro] Ambiente não-interativo e nenhum vídeo encontrado.")
                    return
            else:
                print("[Erro] Ambiente não-interativo e nenhum vídeo encontrado.")
                return

        # Validação do vídeo selecionado
        if not os.path.exists(video_path):
            print(f"[Erro] O arquivo de vídeo '{video_path}' não existe.")
            return
        if not os.path.isfile(video_path):
            print(f"[Erro] O caminho '{video_path}' não é um arquivo válido.")
            return
        if os.path.getsize(video_path) == 0:
            print(f"[Erro] O arquivo de vídeo '{video_path}' está vazio (0 bytes).")
            return
        video_path = os.path.abspath(video_path)
    
    print(f"Vídeo selecionado: {video_path}")

    # 4. Carregar o modelo selecionado
    print("\nCarregando o modelo YOLOv8...")
    model = YOLO(model_path)
    
    # 5. Processar o vídeo com streaming para gerenciar memória RAM
    print("Processando o vídeo (isso pode levar alguns instantes)...")
    limiar_conf = 0.25 if opcao == "2" else 0.15
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.abspath(os.path.join(script_dir, "runs", "detect"))

    results_generator = model.predict(
        source=video_path,
        save=True,
        conf=limiar_conf,
        project=project_dir,
        stream=True
    )
    
    # Iterar sobre os resultados para executar a inferência de todas as frames
    for _ in results_generator:
        pass

    # 6. Identificar a pasta de saída e renomear o vídeo salvo com identificador
    save_dir = model.predictor.save_dir
    output_filename = os.path.basename(video_path)
    base, _ = os.path.splitext(output_filename)
    
    # Procurar por arquivos correspondentes no diretório de saída
    possible_outputs = glob.glob(os.path.join(save_dir, f"{base}.*"))
    
    if possible_outputs:
        original_output = possible_outputs[0]
        actual_ext = os.path.splitext(original_output)[1]
        identificador = "_yolo" if opcao == "2" else "_best"
        novo_nome = f"{base}{identificador}{actual_ext}"
        nova_rota = os.path.join(save_dir, novo_nome)
        
        try:
            if os.path.exists(nova_rota) and os.path.abspath(nova_rota) != os.path.abspath(original_output):
                os.remove(nova_rota)
            os.rename(original_output, nova_rota)
            final_path = nova_rota
        except Exception as e:
            print(f"[Aviso] Não foi possível renomear o arquivo final: {e}")
            final_path = original_output
            
        print("\n=== Processamento de Vídeo Concluído com Sucesso! ===")
        print(f"Vídeo salvo em: {os.path.abspath(final_path)}")
    else:
        print(f"\n=== Processamento Concluído! ===")
        print(f"Resultados salvos no diretório: {os.path.abspath(save_dir)}")

if __name__ == "__main__":
    main()
