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

### 5. 🧠 Módulo de Causa-Raiz & Contexto Urbano (Módulos 2 e 3 do Artigo)
- **Contexto Urbano em Tempo Real (`backend/analytics/contexto_urbano.py`)**: Gerencia o estado de variáveis ambientais e urbanas (chuva forte, horário de pico, eventos/dias de jogo, feriados, obras viárias).
- **Motor Probabilístico de Causa-Raiz (`backend/analytics/causa_raiz.py`)**: Correlaciona cada infração com fatores urbanos e gera a distribuição probabilística das causas prováveis (ex: ausência de segregador, tempo semafórico inadequado, congestionamento, pintura desgastada).
- **Relatórios Enriquecidos**: Cada registro agora armazena `causa_principal`, `causa_confianca`, `cenarios_ativos` e `distribuicao_causas`.

### 6. 📊 Estação Interativa & Dashboard Web (Módulo 4 do Artigo)
- **Dashboard Interativo Streamlit (`frontend/dashboard_streamlit.py`)**:
  - **Área 1**: Simulador de Câmera Urbana com reprodução ao vivo, caixas delimitadoras e alertas interpretáveis ("Infração Detectada — Confiança da IA: 96% | Causa-Raiz: ...").
  - **Área 2**: Simulador de Fatores Externos com controles para alternar cenários em tempo real.
  - **Área 3**: Centro de Diagnóstico Inteligente com gráficos de causas-raiz (Plotly), KPIs e recomendações automatizadas para gestores públicos.
- **Servidor Flask Legado (`frontend/app.py`)**: Mantido para compatibilidade com streaming MJPEG via navegador.

### 7. 🧪 Suíte de Testes Automatizados (`testar_regras.py` & `test_analytics.py`)
- Validação contínua de lógica geométrica, regras espaciais, motor probabilístico e consistência dos relatórios.

---

## 📁 Estrutura do Projeto Atualizada

```
COGNIMOVE/
├── requirements.txt                  ← dependências (ultralytics, streamlit, plotly, pandas, etc.)
├── README.md                         ← documentação principal do projeto
│
├── backend/
│   ├── analytics/                    ← MÓDULOS 2 E 3 (ARTIGO CIENTÍFICO)
│   │   ├── __init__.py
│   │   ├── contexto_urbano.py        ← Módulo 3: Fatores externos e dados urbanos
│   │   └── causa_raiz.py             ← Módulo 2: Motor probabilístico de causa-raiz
│   │
│   ├── models/
│   │   ├── best.pt                   ← pesos do modelo customizado (linhas, faixas, semáforos)
│   │   └── yolov8n.pt                ← pesos base COCO (veículos)
│   │
│   ├── detection/
│   │   ├── monitorar_infracoes.py    ← PONTO DE ENTRADA CLI COM CAUSA-RAIZ
│   │   ├── testar_regras.py          ← suíte de testes de regras
│   │   └── infracoes/
│   │       ├── detector.py           ← orquestrador com integração analítica
│   │       ├── rastreador.py         ← ByteTrack tracker
│   │       ├── evidencias.py         ← gerador de fotos e vídeos MP4
│   │       ├── relatorio.py          ← gravação em CSV e JSON com causa-raiz
│   │       └── regras/
│   │           ├── sinal_vermelho.py     ← infração de semáforo
│   │           ├── faixa_pedestre.py     ← infração de faixa/bike box
│   │           └── bloqueio_cruzamento.py ← infração de retenção
│   │
│   ├── calibration/
│   │   ├── calibrar_camera.py        ← ferramenta interativa OpenCV
│   │   └── presets/                  ← configurações salvas em JSON
│   │
│   └── outputs/
│       ├── evidencias/               ← prints e vídeos recortados
│       └── relatorios/               ← relatórios CSV e JSON enriquecidos
│
└── frontend/
    ├── dashboard_streamlit.py        ← ESTAÇÃO INTERATIVA PRINCIPAL (MÓDULO 4)
    ├── app.py                        ← servidor Flask legado
    ├── templates/                    ← templates HTML do Flask
    └── static/                       ← CSS e JS estáticos
```

---

## 🚀 Como Executar o Sistema

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Iniciar a Estação Interativa (Recomendado — Módulo 4)
Inicia o dashboard completo com simulador de câmera, toggles de cenários urbanos e diagnósticos analíticos:
```bash
streamlit run frontend/dashboard_streamlit.py
```

### 3. Executar o Monitoramento via CLI
Para processamento em lote ou integração com câmeras IP:
```bash
# Executar com janela OpenCV e gravação enriquecida
python backend/detection/monitorar_infracoes.py --source videos_originais/video_teste.mp4 --janela

# Executar com preset específico
python backend/detection/monitorar_infracoes.py --source videos_originais/video_teste.mp4 --preset caetano_alvares --janela
```

## ⚙️ Argumentos CLI
```
--source  -s   Fonte de vídeo (0, rtsp://..., caminho/arquivo.mp4)
--preset  -p   Preset de câmera em calibration/presets/ (sem .json)
--camera  -c   Nome identificador da câmera
--janela  -j   Exibir janela OpenCV durante o processamento
--dashboard -d Iniciar dashboard legado em Flask
--porta   -P   Porta do dashboard legado (padrão: 5000)
```
