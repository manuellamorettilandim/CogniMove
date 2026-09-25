# 🛠️ CogniMove — Notas sobre Scripts de Desenvolvimento e Depuração

Este documento apresenta uma revisão técnica dos três scripts de auxílio ao desenvolvimento localizados em `backend/detection/`: `teste_video.py`, `testar_regras.py` e `identificar_limite.py`.

---

## 📌 Contexto e Status no Projeto

Os arquivos analisados são **ferramentas de apoio visual e testes manuais**, utilizadas durante a prototipagem inicial das regras de infração e calibração. **Eles não fazem parte do pipeline oficial de produção** (`monitorar_infracoes.py`, `detector.py`, `dashboard_streamlit.py`), cujas funcionalidades e cobertura de testes automatizados residem em `backend/tests/`.

---

## 🔍 Relatório de Análise por Arquivo

### 1. `backend/detection/teste_video.py`
- **Propósito:** Executar inferência visual rápida do YOLOv8 (modelo customizado `best.pt` ou modelo base `yolov8n.pt`) em um vídeo e salvar o arquivo renderizado na pasta `outputs/runs/detect/`.
- **Status da Resolução de Vídeo:** ✅ Migrado para `utils_video.py` (`resolver_fonte_video`).
- **Duplicações de Lógica:** Implementa busca manual de arquivos de pesos em `find_best_pt()`. O módulo de produção centralizou o modelo em `backend/models/best.pt`.
- **Pontos Ajustados:** Removidas variáveis não utilizadas no final do script e adicionado aviso claro no cabeçalho.

### 2. `backend/detection/testar_regras.py`
- **Propósito:** Script de teste rápido sem dependências pesadas, utilizando mocks para validar intersecção de segmentos, polígonos, regras de faixa/bloqueio e classificação HSV de semáforos.
- **Status da Resolução de Vídeo:** N/A (não processa arquivos de vídeo, opera exclusivamente com coordenadas sintéticas em memória).
- **Duplicações de Lógica:** Todas as verificações deste script foram formalizadas na suíte oficial de testes unitários em `backend/tests/` (como `test_filtro_classes_veiculares.py`, `test_calibrar_camera.py`, `test_evidencias.py`).
- **Pontos Ajustados:** Mantido como utilitário simples e adicionado o cabeçalho explicativo.

### 3. `backend/detection/identificar_limite.py`
- **Propósito:** Protótipo visual para demonstrar a distância de veículos em relação às linhas de limite calibradas e desenhar um HUD com alertas de aproximação/invasão.
- **Status da Resolução de Vídeo:** ✅ Migrado para `utils_video.py` (`resolver_fonte_video`).
- **Duplicações de Lógica:** Reimplementava regras de colisão e coordenadas hardcoded (`CAMERA_PRESETS`) em vez de carregar os presets salvos em `backend/calibration/presets/*.json` usados por `InfracaoDetector`.
- **Bugs Corrigidos:** O modelo customizado `model_limite` era instanciado mas nunca utilizado durante a inferência dos frames (que chamava apenas `model_yolo`). A variável não utilizada foi ajustada.

---

## 📝 Conclusão e Recomendações

Todos os scripts possuem agora o cabeçalho padronizado alertando que se tratam de ferramentas de desenvolvimento. Para monitoramento de produção com causa-raiz e interface gráfica interativa, utilize sempre:

```bash
# Dashboard Web Principal (Módulo 4)
streamlit run frontend/dashboard_streamlit.py

# Pipeline CLI Principal com Causa-Raiz (Módulo 3)
python backend/detection/monitorar_infracoes.py --source videos_originais/video_teste.mp4 --janela
```
