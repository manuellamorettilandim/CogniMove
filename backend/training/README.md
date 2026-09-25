# 🧠 CogniMove — Guia de Treinamento e Re-treinamento do Modelo YOLOv8

Este guia documenta o fluxo completo para o treinamento do zero, atualização incremental de dados e re-treinamento do modelo de visão computacional (`backend/models/best.pt`) utilizado no projeto **CogniMove**.

---

## 📋 Sumário
1. [Pré-requisitos](#-1-pré-requisitos)
2. [Passo 1: Adicionar Novos Vídeos para a Classe Limite](#-passo-1-adicionar-novos-vídeos-para-a-classe-limite)
3. [Passo 2: Adicionar ou Atualizar Datasets do Roboflow](#-passo-2-adicionar-ou-atualizar-datasets-do-roboflow)
4. [Passo 3: Executar a Fusão dos Datasets (ETL)](#-passo-3-executar-a-fusão-dos-datasets-etl)
5. [Passo 4: Executar o Treinamento](#-passo-4-executar-o-treinamento)
6. [Passo 5: Avaliação do Novo Modelo](#-passo-5-avaliação-do-novo-modelo)
7. [Gerenciamento de Backups e Rollback](#-gerenciamento-de-backups-e-rollback)

---

## 🛠️ 1. Pré-requisitos

Para executar o pipeline de preparação de dados e treinamento, certifique-se de ter instalado as dependências Python específicas do módulo de treinamento:

```bash
pip install ultralytics roboflow opencv-python numpy pyyaml python-dotenv
```

---

## 🎥 Passo 1: Adicionar Novos Vídeos para a Classe "Limite"

O script `backend/training/dataset_limite.py` extrai frames dos vídeos de teste, valida a resolução esperada de cada vídeo e aplica *data augmentation* (brilho, contraste, desfoque e flip horizontal) para gerar o dataset sintético da classe `Limite`.

### Como adicionar um novo vídeo ao dataset de limite:
1. Coloque o novo arquivo de vídeo na pasta `videos_teste/` ou `videos_originais/` (ex: `videos_teste/video_teste5.mp4`).
2. Abra `backend/training/dataset_limite.py` e adicione a configuração do vídeo na estrutura `video_configs`:

```python
video_configs = {
    "video_teste5.mp4": {
        "resolucao_esperada": (1920, 1080),  # (largura, altura) exata do vídeo
        "boxes": [
            # Formato YOLO normalizado: (classe_id, x_centro, y_centro, largura, altura)
            (0, 0.500, 0.750, 0.600, 0.050),
        ],
    },
}
```

3. Execute o script para extrair frames e gerar o dataset sintético:

```bash
python backend/training/dataset_limite.py
```

**Saída esperada:** Diretório `backend/training/datasets/dataset_limite/` criado com as pastas `train/`, `valid/`, `test/` e o arquivo `data_limite.yaml`.

---

## ☁️ Passo 2: Adicionar ou Atualizar Datasets do Roboflow

O script `backend/training/yolo_roboflow_predict.py` faz o download seguro do dataset anotado na nuvem via API do Roboflow.

### 🔒 Configuração de Segurança (`.env`):
**NUNCA** inclua chaves de API diretamente no código-fonte.
1. Crie ou edite o arquivo `.env` na raiz do projeto:

```env
ROBOFLOW_API_KEY=sua_chave_privada_do_roboflow_aqui
```

2. Execute o script de download:

```bash
python backend/training/yolo_roboflow_predict.py
```

**Saída esperada:** Dataset baixado em `backend/training/datasets/Imagens-Cognimove-1/` contendo as imagens e anotações originais.

---

## 🔀 Passo 3: Executar a Fusão dos Datasets (ETL)

O script `backend/training/merge_datasets.py` realiza a limpeza, sanitização, remapeamento de classes e fusão dos datasets local e cloud em um único dataset unificado.

- **Limpeza Automática:** O diretório de destino unificado é completamente limpo antes da fusão para garantir que anotações desatualizadas ou descartadas não corrompam o treino.
- **Prefixo dos Arquivos:** Adiciona o prefixo `sintetico_` para imagens locais e `robo_` para imagens do Roboflow para evitar colisão de nomes.

Execute o merge com o comando:

```bash
python backend/training/merge_datasets.py
```

**Saída esperada:** Estrutura unificada criada em:
```
backend/training/datasets/unificado/
├── data.yaml
├── images/
│   ├── train/
│   └── val/
└── labels/
    ├── train/
    └── val/
```

---

## 🚀 Passo 4: Executar o Treinamento

O script `backend/training/yolo_train.py` orquestra o treinamento do modelo YOLOv8 utilizando o dataset unificado.

### Configuração Atual dos Hiperparâmetros:

No código atual de `backend/training/yolo_train.py`, os hiperparâmetros de treinamento estão definidos dentro da função `main()` como:

```python
# Configuração dos parâmetros de treino em yolo_train.py
epochs = 50
imgsz = 640
run_name = "treino_fecart_unificado"

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
```

> [!NOTE]
> **Valores Atuais do Projeto:** Os valores exibidos no bloco acima (`epochs=50`, `imgsz=640`, `batch=8`, `run_name="treino_fecart_unificado"`) refletem exatamente a configuração ativa no momento. Para alterar o número de épocas, a resolução, o tamanho do batch ou o nome do experimento, edite diretamente as variáveis `epochs`, `imgsz`, `run_name` e o parâmetro `batch` dentro da função `main()` em `backend/training/yolo_train.py`.

### Executando o Treinamento:

```bash
python backend/training/yolo_train.py
```

**O que acontece ao final do treino:**
1. Se já existir um modelo de produção em `backend/models/best.pt`, o script gera um **backup automático com timestamp** (ex: `best.pt.bak.20260906_143000`).
2. Copia os novos pesos recém-treinados por cima de `backend/models/best.pt`.

---

## 📈 Passo 5: Avaliação do Novo Modelo

Antes de utilizar o modelo recém-treinado em produção, avalie seu desempenho em vídeos de teste usando a ferramenta de avaliação:

```bash
# Avaliar modelo em um vídeo específico
python backend/training/avaliar_modelo.py --fonte videos_teste/video_teste4.mp4

# Avaliar modelo em todos os vídeos e salvar relatório CSV
python backend/training/avaliar_modelo.py --fonte videos_originais/ --salvar-csv
```

---

## 🛡️ Gerenciamento de Backups e Rollback

### 🧹 Limpeza Periódica de Backups
Como cada treinamento cria um backup timestamped `best.pt.bak.YYYYMMDD_HHMMSS` em `backend/models/`, esses arquivos podem acumular espaço em disco ao longo do tempo. Recomenda-se realizar uma limpeza manual periódica mantendo apenas os backups mais recentes.

**No Linux / macOS:**
```bash
# Listar backups
ls -lh backend/models/best.pt.bak.*

# Remover backups antigos (manualmente selecionados)
rm backend/models/best.pt.bak.20260901_*
```

**No Windows (PowerShell):**
```powershell
# Listar backups
Get-ChildItem backend/models/best.pt.bak.*

# Remover backups antigos
Remove-Item backend/models/best.pt.bak.20260901_*
```

### ⏪ Como Fazer Rollback (Reverter para um Modelo Anterior)
Se um novo treinamento produzir resultados piores que o modelo anterior, você pode restaurar instantaneamente a versão anterior a partir de um dos backups:

**No Linux / macOS:**
```bash
cp backend/models/best.pt.bak.20260905_120000 backend/models/best.pt
```

**No Windows (PowerShell):**
```powershell
Copy-Item backend/models/best.pt.bak.20260905_120000 backend/models/best.pt -Force
```
