"""
CogniMove — Script de Desenvolvimento / Depuração Manual: teste_video.py

AVISO: Este script é uma ferramenta auxiliar de desenvolvimento local para testes
rápidos de inferência em vídeo. NÃO faz parte do pipeline de produção testado
(monitorar_infracoes.py / detector.py). Veja backend/detection/NOTAS_SCRIPTS_DEV.md.
"""
import os
import glob
import sys
import argparse
from pathlib import Path
from ultralytics import YOLO

# Garantir imports relativos de utils_video
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
_ROOT = _BACKEND.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from utils_video import resolver_fonte_video, PASTAS_VIDEO, EXTENSOES_VIDEO

def find_best_pt():
    """
    Localiza o arquivo de pesos 'best.pt' em backend/models/ ou nas pastas de treinamento.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # detection/ -> backend/ -> project_root/
    backend_dir  = os.path.abspath(os.path.join(script_dir, ".."))
    models_dir   = os.path.join(backend_dir, "models")
    outputs_dir  = os.path.join(backend_dir, "outputs", "runs", "detect")
    
    candidates = [
        os.path.join(models_dir, "best.pt"),
    ]
    
    # Procurar nas pastas de treinamento em outputs/runs/detect/train*/weights/
    runs_pattern = os.path.join(outputs_dir, "train*", "weights", "best.pt")
    candidates.extend(glob.glob(runs_pattern))
        
    valid_candidates = [f for f in set(candidates) if os.path.isfile(f) and os.path.getsize(f) > 0]
    
    if not valid_candidates:
        raise FileNotFoundError(
            "Não foi possível encontrar o arquivo de pesos 'best.pt' em backend/models/ ou em outputs/runs/. "
            "Certifique-se de que o modelo treinado está no diretório correto."
        )
    
    # Retorna o arquivo modificado mais recentemente
    valid_candidates.sort(key=os.path.getmtime, reverse=True)
    return os.path.abspath(valid_candidates[0])

def find_video_file():
    """
    Localiza automaticamente um arquivo de vídeo em videos_teste/ e videos_originais/ na raiz do projeto.
    """
    search_dirs = [_ROOT / pasta for pasta in PASTAS_VIDEO] + [_HERE]
    video_files = []
    
    for d in search_dirs:
        if d.exists():
            for ext in EXTENSOES_VIDEO:
                video_files.extend(d.glob(f"*{ext}"))
                video_files.extend(d.glob(f"*{ext.upper()}"))
            
    valid_videos = [str(f) for f in set(video_files) if f.is_file() and f.stat().st_size > 0]
    
    if not valid_videos:
        return None
        
    # Ordena pelo mais recentemente modificado
    valid_videos.sort(key=os.path.getmtime, reverse=True)
    return os.path.abspath(valid_videos[0])

def main():
    parser = argparse.ArgumentParser(description="Teste de inferência em vídeo com YOLOv8 - CogniMove")
    parser.add_argument("video", nargs="?", help="Caminho do arquivo de vídeo de teste")
    parser.add_argument("opcao", nargs="?", choices=["1", "2", "3"], help="Opção: 1 (best.pt - Limite/Faixas), 2 (yolov8n.pt), 3 (Monitor Integrado de Limite)")
    args = parser.parse_args()

    print("=== Inicializando Teste de Vídeo com YOLOv8 - CogniMove ===")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.dirname(script_dir)
    
    # 1. Definir opção do modelo
    opcao = args.opcao
    if not opcao:
        print("Escolha o modo de detecção:")
        print("1 - Seu modelo personalizado (best.pt - Reconhecimento de 'Limite', 'Faixa_Pedestre', 'Semaforo')")
        print("2 - Modelo padrão YOLOv8 (yolov8n.pt - Detecção geral COCO)")
        print("3 - Monitor Integrado de Limite e Veículos (Identificação + Alerta de Invasão de Faixa)")
        
        if sys.stdin.isatty():
            try:
                opcao = input("Digite a opção (1, 2 ou 3) [Padrão: 1]: ").strip()
                if not opcao:
                    opcao = "1"
            except Exception:
                opcao = "1"
        else:
            print("Ambiente não-interativo detectado. Usando opção padrão: 1")
            opcao = "1"

    # Se a opção 3 for selecionada, redirecionar para o módulo identificar_limite
    if opcao == "3":
        try:
            # Adicionar backend/detection ao path para import
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import identificar_limite
            video_escolhido = args.video if args.video else find_video_file()
            if not video_escolhido:
                print("[Erro] Nenhum vídeo encontrado para processamento.")
                return
            identificar_limite.processar_video(video_escolhido)
            return
        except Exception as e:
            print(f"[Erro] Falha ao executar o monitor integrado: {e}")
            return

    # 2. Localizar pesos do modelo
    script_dir   = os.path.dirname(os.path.abspath(__file__))
    backend_dir  = os.path.abspath(os.path.join(script_dir, ".."))
    models_dir   = os.path.join(backend_dir, "models")
    outputs_dir  = os.path.abspath(os.path.join(backend_dir, "outputs", "runs", "detect"))

    if opcao == "2":
        local_yolo = os.path.join(models_dir, "yolov8n.pt")
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
        resolved = resolver_fonte_video(video_path, root=_ROOT)
        if not os.path.exists(str(resolved)):
            print(f"[Erro] O arquivo de vídeo '{video_path}' não existe.")
            return
        video_path = str(resolved)
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
                        resolved_esc = resolver_fonte_video(escolha, root=_ROOT)
                        video_path = str(resolved_esc) if os.path.exists(str(resolved_esc)) else escolha
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
    print(f"Classes configuradas no modelo: {model.names}")
    
    # 5. Processar o vídeo com streaming para gerenciar memória RAM
    print("Processando o vídeo (isso pode levar alguns instantes)...")
    limiar_conf = 0.25 if opcao == "2" else 0.15
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.abspath(os.path.join(script_dir, "runs", "detect"))

    results_generator = model.predict(
        source=video_path,
        save=True,
        conf=limiar_conf,
        project=outputs_dir,
        stream=True
    )
    
    # Iterar sobre os resultados para executar a inferência de todas as frames
    frame_count = 0
    for _ in results_generator:
        frame_count += 1
        # Para vídeos muito longos de 3 horas durante testes, processar até 500 frames
        if frame_count >= 500:
            break

    # 6. Identificar a pasta de saída e renomear o vídeo salvo com identificador
    save_dir = model.predictor.save_dir
    output_filename = os.path.basename(video_path)
    base, _ = os.path.splitext(output_filename)
    
    possible_outputs = glob.glob(os.path.join(save_dir, f"{base}.*"))
    
    if possible_outputs:
        original_output = possible_outputs[0]
        actual_ext = os.path.splitext(original_output)[1]
        identificador = "_yolo" if opcao == "2" else "_limite_best"
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
        print(f"Vídeo com classes detectadas salvo em: {os.path.abspath(final_path)}")
    else:
        print(f"\n=== Processamento Concluído! ===")
        print(f"Resultados salvos no diretório: {os.path.abspath(save_dir)}")

if __name__ == "__main__":
    main()
