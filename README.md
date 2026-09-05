# 🚦 CogniMove — Sistema Inteligente de Detecção de Infrações de Trânsito

O **CogniMove** é uma solução completa e moderna de visão computacional voltada para o monitoramento urbano, detecção de infrações de trânsito em tempo real (avanço de sinal vermelho, invasão de faixa/bike box e bloqueio de cruzamento) com rastreamento persistente de veículos e dashboard web interativo.

---

## 🎯 O Que Foi Feito Até Agora

### 1. 🧠 Módulo de Treinamento & Visão Computacional (YOLOv8)
- **Detecção de Objetos (YOLOv8)**: Integração com modelo `yolov8n.pt` para detecção de veículos (carros, motos, ônibus, caminhões) e modelo customizado `best.pt` treinado para identificar marcas viárias e semáforos.
- **Rastreamento Multi-Objeto (ByteTrack)**: Implementação do módulo `rastreador.py` que atribui IDs únicos e persistentes para cada veículo, permitindo acompanhar trajetórias e prevenir alertas duplicados.
- **Classificação HSV de Semáforos**: Algoritmo de análise de cor no espaço de cores HSV para identificar os estados do semáforo (Vermelho, Amarelo, Verde) com tolerância a variações de iluminação.

### 2. 🚨 Regras de Infração Especializadas (`backend/detection/infracoes/regras/`)
- **Avanço de Sinal Vermelho (`sinal_vermelho.py`)**: Monitora quando um veículo cruza a linha de retenção enquanto o semáforo correspondente está na fase vermelha.
- **Invasão de Faixa de Pedestres / Bike Box (`faixa_pedestre.py`)**: Detecta se o veículo invade o polígono delimitador da faixa de pedestres ou área reservada para ciclistas durante a parada.
- **Bloqueio de Cruzamento (`bloqueio_cruzamento.py`)**: Mede o tempo de permanência de um veículo parado dentro do polígono da "caixa amarela" do cruzamento (gera alerta se permanecer retido por mais de 5 segundos).

### 3. 📐 Ferramenta de Calibração Interativa (`backend/calibration/calibrar_camera.py`)
- Interface gráfica com OpenCV que permite desenhar diretamente sobre o frame do vídeo:
  - **Linha de Retenção (L)**: 2 pontos indicando onde os veículos devem parar.
  - **Polígono da Faixa / Bike Box (P)**: Marcação espacial da área protegida.
  - **Zona de Cruzamento (I)**: Marcação do polígono de intersecção.
- Salvamento automático em arquivos JSON na pasta `backend/calibration/presets/` (ex: `caetano_alvares.json`, `maria_paula.json`).

### 4. 📸 Produção Automática de Evidências (`evidencias.py` & `relatorio.py`)
- **Screenshots da Infração**: Geração de imagens `.jpg` anotadas com a caixa delimitadora do veículo infrator, tipo de infração e timestamp.
- **Mini-Clips em MP4**: Buffer circular de vídeo que grava automaticamente 3 segundos **antes** e 2 segundos **depois** do evento de infração.
- **Relatórios Estruturados**: Exportação em tempo real para arquivos `.csv` e `.json` em `backend/outputs/relatorios/`.

### 5. 🌐 Dashboard Web Interativo (Flask)
- Servidor web Flask (`frontend/app.py`) fornecendo:
  - Streaming de vídeo ao vivo (MJPEG) com overlays de detecção.
  - Painel de estatísticas (total de infrações por categoria).
  - Feed em tempo real de infrações recentes com fotos e links para download.
  - Seleção dinâmica de câmeras/fontes de vídeo e carregamento de presets.

### 6. 🧪 Suíte de Testes Automatizados (`testar_regras.py`)
- Script de testes unitários para validação de lógica de detecção, regras de cruzamento, geração de relatórios e inferências HSV sem depender de vídeo físico.

---

## 🎓 Tipos de Treinamento Utilizados

No projeto CogniMove, foram estruturadas e utilizadas 3 estratégias complementares de treinamento e fine-tuning:

```
                      ┌──────────────────────────────────────────┐
                      │    YOLOv8 Base (Pré-treinado COCO)       │
                      └────────────────────┬─────────────────────┘
                                           │
         ┌─────────────────────────────────┴─────────────────────────────────┐
         ▼                                                                   ▼
┌─────────────────────────────────┐                         ┌─────────────────────────────────┐
│   Treinamento Sintético Local   │                         │    Treinamento Cloud Roboflow   │
│ (`dataset_limite.py` + Augment) │                         │  (`yolo_roboflow_predict.py`)   │
└────────────────┬────────────────┘                         └────────────────┬────────────────┘
                 │                                                           │
                 └─────────────────────────┬─────────────────────────────────┘
                                           ▼
                            ┌──────────────────────────────┐
                            │ Pesos Finais: `best.pt`      │
                            │ (Classes: Limite, Faixa,     │
                            │  Semáforo)                   │
                            └──────────────────────────────┘
```

### 1. Fine-Tuning por Transfer Learning (YOLOv8)
- **Modelo Base**: `yolov8n.pt` (YOLOv8 Nano, leve e otimizado para inferência em tempo real no CPU/GPU).
- **Técnica**: Congelamento de camadas convolucionais iniciais para reaproveitar extratores de características genéricos e ajuste das camadas finais para as classes específicas do domínio viário:
  - `0: Limite` (Linha de retenção de parada obrigatória)
  - `1: Faixa_Pedestre` (Zebrada ou Bike Box)
  - `2: Semaforo` (Corpo do semáforo)

### 2. Geração de Dataset Sintético & Data Augmentation Local (`dataset_limite.py`)
- **Amostragem de Vídeos**: Extração de frames espaçados a partir de vídeos reais de tráfego (`videos_originais/` e `videos_teste/`).
- **Data Augmentation**: Aplicação programática de transformações para simular variações de clima, horário e qualidade de câmera:
  - **Ajuste de Brilho e Contraste**: Fator aleatório de 0.7 a 1.3.
  - **Ruído Gaussiano**: Simulação de granulação noturna e chuva.
  - **Desfoque (Blur)**: Simulação de perda de foco ou chuva no vidro da câmera.
  - **Flip Horizontal**: Inversão da pista mantendo as coordenadas Bounding Box sincronizadas.
- **Divisão do Dataset**: 70% Treino, 20% Validação, 10% Teste.

### 3. Treinamento & Anotação via Roboflow Cloud (`yolo_roboflow_predict.py`)
- Integration via API Roboflow (`ROBOFLOW_API_KEY`) no workspace `mell-sowg7` (projeto `imagens-cognimove`).
- Permite rotulagem em nuvem, exportação direta no formato YOLOv8 e treinamento com datasets expandidos da comunidade.

---

## 💻 Como Treinar o Modelo pelo Terminal

### Opção 1: Usando o Script Automático do Projeto (Recomendado)
```bash
python backend/training/yolo_train.py
```

### Opção 2: Usando a CLI Direta do Ultralytics
```bash
yolo detect train data=backend/training/configs/data_limite.yaml model=yolov8n.pt epochs=25 imgsz=640 batch=8
```

---

## 📁 Estrutura do Projeto

```
Cognimove_Melissa/
├── .env                              ← chave da API do Roboflow
├── requirements.txt                  ← dependências do projeto
├── README.md                         ← documentação principal
│
├── backend/
│   ├── models/
│   │   ├── best.pt                   ← pesos do modelo customizado
│   │   └── yolov8n.pt                ← pesos base COCO (veículos)
│   │
│   ├── detection/
│   │   ├── monitorar_infracoes.py    ← PONTO DE ENTRADA PRINCIPAL
│   │   ├── testar_regras.py          ← suíte de testes unitários
│   │   └── infracoes/
│   │       ├── detector.py           ← orquestrador de detecção
│   │       ├── rastreador.py         ← ByteTrack tracker
│   │       ├── evidencias.py         ← gerador de fotos e vídeos MP4
│   │       ├── relatorio.py          ← gravação em CSV e JSON
│   │       └── regras/
│   │           ├── sinal_vermelho.py     ← infração de semáforo
│   │           ├── faixa_pedestre.py     ← infração de faixa/bike box
│   │           └── bloqueio_cruzamento.py ← infração de retenção
│   │
│   ├── calibration/
│   │   ├── calibrar_camera.py        ← ferramenta interativa OpenCV
│   │   └── presets/                  ← configurações salvas em JSON
│   │
│   ├── training/
│   │   ├── yolo_train.py             ← pipeline automático de treino
│   │   ├── dataset_limite.py         ← gerador de dataset sintético
│   │   └── yolo_roboflow_predict.py  ← integração Roboflow Cloud
│   │
│   └── outputs/                      ← evidências e relatórios
│
└── frontend/
    ├── app.py                        ← servidor Flask do Dashboard
    ├── templates/index.html          ← interface web
    └── static/                       ← CSS e JS do dashboard
```

---

## 🚀 Como Executar o Sistema

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Rodar o Sistema com Dashboard Web
```bash
python backend/detection/monitorar_infracoes.py --source videos_teste/video_teste.mp4 --dashboard
# Acesse no navegador: http://localhost:5000
```

## ⚙️ Argumentos CLI
```
--source  -s   Fonte de vídeo (0, rtsp://..., arquivo.mp4)
--preset  -p   Preset de câmera (nome sem .json)
--camera  -c   Nome identificador da câmera
--janela  -j   Exibir janela OpenCV
--dashboard -d Iniciar dashboard web Flask
--porta   -P   Porta do dashboard (padrão: 5000)
```
