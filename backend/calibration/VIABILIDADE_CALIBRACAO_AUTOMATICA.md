# 📐 CogniMove — Estudo de Viabilidade: Calibração Assistida por IA (Auto-Sugestão)

## 📌 Contexto e Motivação
Atualmente, o processo de calibração de uma nova câmera no CogniMove requer a marcação manual de cada elemento geométrico (linhas de retenção semafórica, linhas de faixa de pedestres, polígonos de bike box e zonas de intersecção) utilizando a ferramenta interativa [`calibrar_camera.py`](backend/calibration/calibrar_camera.py).

Embora a calibração manual seja extremamente precisa, ela se torna um gargalo operacional quando o sistema precisa ser escalado para dezenas de interseções urbanas ou novos vídeos de teste.

Este documento avalia a viabilidade técnica de utilizar o modelo YOLOv8 treinado no projeto ([`backend/models/best.pt`](backend/models/best.pt)) para **sugerir automaticamente a posição inicial de linhas e polígonos**, acelerando a calibração sem comprometer a precisão.

---

## 🧠 1. Uso do Modelo `best.pt` para Sugestão Inicial

O modelo customizado do CogniMove (`best.pt`) já foi treinado especificamente para reconhecer marcações viárias e elementos de sinalização urbana nas seguintes classes:
- `0: Limite` (Linha de retenção ou parada)
- `1: Faixa_Pedestre` (Marcações zebradas e bike boxes)
- `2: Semaforo` (Foco semafórico)

### Fluxo Proposto para Auto-Sugestão:
1. Durante a inicialização da calibração (ou ao pressionar a tecla de atalho `A` - *Auto-Sugestão*), o sistema captura um frame de referência (`_grab_frame()`).
2. O modelo `best.pt` executa uma inferência de passagem única (*single-pass inference*) no frame com um limiar de confiança ajustável (ex.: `conf >= 0.25`).
3. As detecções resultantes são processadas por uma heurística geométrica para gerar candidatos a **linhas** e **polígonos**.
4. As sugestões são desenhadas na tela em um estado temporário/rascunho com cor diferenciada (ex.: Roxo/Magenta `(255, 0, 255)`).
5. O operador humano analisa visualmente as sugestões e decide aceitar (tecla `Y`), descartar (tecla `N`) ou refinar manualmente antes de salvar o arquivo JSON de preset.

---

## 📐 2. Heurísticas Geométricas de Conversão

Como a inferência do YOLOv8 retorna caixas delimitadoras (*bounding boxes* 2D no formato `[x1, y1, x2, y2]`), é necessária uma conversão simples para os formatos geométricos esperados pelas regras de infração (`line`, `stop_line`, `polygon` e `intersection`):

### A. Conversão para Polígonos (`polygon` / `intersection`):
Para detecções da classe **`Faixa_Pedestre`**:
- A bounding box `[x1, y1, x2, y2]` é convertida diretamente para os 4 vértices do retângulo delimitador:
  $$\text{Vértices} = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]$$
- Esse polígono retangular inicial serve como base para marcação de *bike boxes* ou faixas de pedestres.

### B. Conversão para Linhas (`stop_line` / `line`):
Para detecções da classe **`Limite`**:
- Se a largura da caixa for maior que a altura ($w > h$ - caso típico de linhas de retenção horizontais no asfalto), utiliza-se o segmento inferior onde o veículo entraria em contato:
  $$\text{Linha Horizontal} = [(x1, y2), (x2, y2)]$$
- Se a altura for maior que a largura ($h > w$ - linhas verticais em ângulo acentuado), utiliza-se o segmento vertical central:
  $$\text{Linha Vertical} = [\left(\frac{x1+x2}{2}, y1\right), \left(\frac{x1+x2}{2}, y2\right)]$$

---

## ⚠️ 3. Análise de Riscos e Estratégia de Mitigação

### Riscos Identificados:
1. **Distorção de Perspectiva 3D:** Bounding boxes retangulares 2D não capturam a perspectiva trapezoidal real de ruas vistas em ângulo. Um polígono retangular gerado via bbox pode cobrir áreas indesejadas do asfalto se não for ajustado.
2. **Falsos Positivos do Modelo:** Placas publicitárias, faixas zebradas fora do cruzamento ou reflexos podem gerar sugestões de linhas de retenção espúrias.
3. **Falsa Confiança do Operador:** Aceitar sugestões automáticas sem verificação visual atenta pode levar a presets desalinhados, resultando em falsos positivos ou falsos negativos nas regras de infração em produção.

### Estratégia de Mitigação (Princípio *Human-in-the-Loop*):
- **Estritamente Aditivo e Opcional:** A auto-sugestão **nunca** substitui o controle manual nem salva presets de forma autônoma.
- **Estado Visual Temporário:** As sugestões aparecem em uma cor especial (Magenta) com indicação textual clara `[SUGESTÃO IA]`.
- **Confirmação Explícita Obrigatória:** As sugestões só são incorporadas aos conjuntos ativos de calibração se o operador pressionar explicitamente a tecla `Y` (*Yes*). Pressionar `N` (*No*) descarta instantaneamente o rascunho sem alterar a seleção atual.

---

## 💡 4. Conclusão e Recomendação

A implementação de uma funcionalidade de auto-sugestão em [`calibrar_camera.py`](backend/calibration/calibrar_camera.py) é **amplamente viável, segura e benéfica**, desde que siga a abordagem assistiva com confirmação humana (*Human-in-the-Loop*).

Recomenda-se a adição do protótipo simples acionado pela tecla `A` na ferramenta interativa OpenCV.
