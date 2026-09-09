# CogniMove — contexto do projeto

Cole este texto nas instruções do projeto, ou anexe o arquivo ao conhecimento do projeto.
Última atualização: 7 de setembro de 2026.

---

## O que é

O CogniMove é uma plataforma de detecção automática de infrações de trânsito por visão
computacional, com uma camada analítica que tenta explicar **por que** as infrações
acontecem em determinado ponto, em vez de apenas registrá-las. A proposta está descrita
no artigo "CogniMove: Sistema Inteligente de Detecção Visual de Infrações com Análise de
Causa-Raiz e Integração de Dados Urbanos para Apoio à Mobilidade Urbana" (Manuella Moretti
Landim, Melissa Nunes de Oliveira e Raíssa Ramos, junho de 2026).

A ideia central do artigo é deslocar a fiscalização eletrônica da lógica punitiva para uma
lógica diagnóstica. Um avanço de sinal vermelho recorrente num cruzamento pode indicar tempo
semafórico mal dimensionado, e não só imprudência; invasões repetidas de faixa exclusiva
podem apontar ausência de segregador físico. O sistema correlaciona cada evento detectado
com fatores urbanos (chuva, horário de pico, feriado, obra, evento de grande porte) e devolve
uma distribuição probabilística de causas prováveis, pensada como apoio à decisão de gestores
públicos.

O projeto é um trabalho de colégio técnico, apresentado numa feira de IA com tema de cidades
inteligentes. O público do estande são famílias de alunos e empresas que podem contratar os
alunos. A equipe tem três pessoas.

## Os quatro módulos do artigo e o estado real de cada um

**Módulo 1 — detecção visual.** Implementado. YOLOv8 (`yolov8n.pt`) para veículos, BoTSORT
para rastreamento com IDs persistentes, e um modelo próprio (`best.pt`) treinado para marcações
viárias. Três regras espaço-temporais: avanço de sinal vermelho, invasão de faixa de pedestres
e bloqueio de cruzamento. Gera evidências (screenshot anotado e clipe MP4 com buffer circular
de 3 s antes e 2 s depois) e relatórios em CSV e JSONL.

**Módulo 2 — causa-raiz.** Implementado em `backend/analytics/causa_raiz.py`. Importante: as
probabilidades base e os modificadores contextuais foram **definidos pela equipe a partir da
literatura, não aprendidos a partir de dados**. Isso precisa ser dito com todas as letras
sempre que o assunto aparecer, na interface e na apresentação. Tratar esses números como
previsão de modelo é o erro mais fácil de um avaliador técnico apontar.

**Módulo 3 — dados urbanos.** Parcialmente implementado. Existe
`backend/analytics/contexto_tempo_real.py` com consulta real de feriado, chuva, jogo e horário
de pico a partir de uma data e hora, mas o dashboard ainda usa cinco interruptores manuais e
não importa esse arquivo. Reconectar isso é tarefa em aberto.

**Módulo 4 — estação interativa.** É a parte que a equipe está construindo agora, e é o foco
do trabalho atual. Existe um dashboard Streamlit (`frontend/dashboard_streamlit.py`) dividido
nas três áreas descritas no artigo, e está sendo redesenhada uma tela específica para a feira,
já que a interação atual foi considerada inadequada para o público e para o contexto do estande.

## O que está sendo construído agora (a interatividade)

O estande tem um PC sem webcam, uma tela só, e o público prioritário são recrutadores. A
interação foi redesenhada em torno de três coisas, todas rodando a partir de vídeos
pré-renderizados para não depender de GPU no dia:

1. **Comparação com e sem rastreamento.** Dois players do mesmo trecho, sincronizados por
   índice de quadro, com contadores de alertas. Sem identidade persistente entre quadros, as
   regras que dependem da posição anterior (avanço de sinal e cruzamento de linha) param de
   disparar, e as regras estáticas passam a alertar o mesmo veículo em todo quadro. O sistema
   erra dos dois lados, e isso demonstra visualmente por que a camada de rastreamento existe.
2. **Raio-x do pipeline em cinco camadas.** Frame cru, detecção, rastreamento, geometria
   calibrada e regras. Trocar de camada não pode reiniciar a cena.
3. **Cronômetro em anel do bloqueio de cruzamento**, para tornar visível uma regra que hoje
   dispara sem aviso.

A tela roda em modo quiosque, com poucos controles, volta sozinha ao estado inicial depois de
90 segundos sem interação, e nunca mostra caminho de arquivo, upload ou traceback.

## Estrutura do repositório

```
backend/
  analytics/      causa_raiz.py, contexto_urbano.py, contexto_tempo_real.py
  calibration/    calibrar_camera.py, validar_presets.py, presets/*.json
  detection/      monitorar_infracoes.py, utils_video.py
    infracoes/    detector.py, rastreador.py, evidencias.py, relatorio.py
      regras/     sinal_vermelho.py, faixa_pedestre.py, bloqueio_cruzamento.py
  models/         best.pt (Limite, Faixa_Pedestre, Semaforo), yolov8n.pt
  outputs/        evidencias/, relatorios/
  tests/          suíte pytest com mocks de torch/ultralytics
frontend/         dashboard_streamlit.py, app.py (Flask legado), recomendacoes.py
videos_originais/ gravações das câmeras da CET-SP
```

## Semântica dos presets (fonte recorrente de erro)

Cada cruzamento tem um JSON em `backend/calibration/presets/` com quatro tipos de forma, e
cada uma alimenta uma regra diferente:

- `stop_lines` — consumido pela regra de sinal vermelho. A regra verifica se o segmento entre
  a posição **anterior** e a **atual** do veículo cruza a linha. A linha precisa estar no
  asfalto, atravessando a via. Linha desenhada sobre o semáforo nunca é cruzada por veículo
  nenhum e a regra jamais dispara.
- `lines` — mesma lógica de cruzamento, usada pela regra de faixa para limites e bike box.
- `polygons` — a faixa de pedestres. Dispara quando o ponto inferior do veículo entra na área.
- `intersection_polygons` — a caixa amarela. Dispara quando o veículo permanece dentro por
  mais de N segundos.

Coordenadas ficam em resolução de referência (`ref_width`, `ref_height`) e são escaladas em
tempo de execução por `scale_preset()`.

## Fatos medidos que valem mais que suposição

- **O `best.pt` não detecta semáforo nessas câmeras.** Zero detecções da classe `Semaforo` em
  escalas de 1x a 4x e confiança até 0.05. Como consequência, o estado do semáforo fica
  `unknown` em 100% dos quadros e a regra de sinal vermelho retorna antes de olhar qualquer
  veículo. A saída encontrada é aproveitar que a câmera é fixa: marcar a região do semáforo
  uma vez no preset e rodar o `classify_traffic_light_hsv` que já existe nessa região. Testado
  e funciona, com leituras estáveis de vermelho e verde ao longo do ciclo.
- **O rastreador perde identidade rápido a 5 fps.** A vida mediana de um ID é de 1,6 a 3,6
  segundos, enquanto o bloqueio de cruzamento exige 25 quadros seguidos com o mesmo ID dentro
  da zona. Por isso essa regra quase nunca dispara nesses vídeos, e o limiar precisa cair para
  algo em torno de 2,5 s.
- **Os vídeos são gravações reais das câmeras da CET-SP**, com quase três horas cada, a 5 ou 6
  quadros por segundo, em 352×240 e 480×270. A imagem picotada é a taxa de captura da câmera,
  não defeito do sistema.
- **A regra de invasão de faixa funciona** e é a que mais aparece: 15 eventos em 80 segundos
  num dos vídeos.

## Como trabalhar neste projeto

- Rodar `pytest backend/tests/ -v` antes e depois de qualquer alteração. A suíte usa mocks e
  é rápida.
- Rodar `python backend/calibration/validar_presets.py` sempre que um preset mudar. Ele mede
  quantas infrações de cada tipo saem em 400 quadros e acusa polígonos auto-intersectantes,
  zonas sobrepostas, linhas curtas demais e `stop_lines` vazio.
- Nunca inventar coordenadas de linha ou polígono. Calibração é trabalho visual humano, feito
  com `calibrar_camera.py` olhando o vídeo.
- Não usar a auto-sugestão por IA da ferramenta de calibração (teclas `A` e `Y`): ela converte
  qualquer detecção da classe `Limite` em linha de retenção e polui o preset.
- Evitar mudanças grandes de arquitetura. O projeto está em fase de entrega e o que existe
  funciona.
- Ao falar do módulo de causa-raiz, sempre deixar claro que os pesos são hipóteses assumidas
  pela equipe.
