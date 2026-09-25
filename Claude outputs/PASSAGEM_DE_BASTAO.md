# CogniMove — Passagem de Bastão

**De:** Manuella (Pessoa 1 — backend / contexto urbano)
**Data:** 07/09/2026
**Branch:** `pessoa1-contexto-real`

Leia até o fim antes de mexer em qualquer coisa. A parte 3 tem dois problemas que podem inviabilizar a demonstração e que **não são de código** — se ninguém tratar deles hoje, o resto não adianta.

---

## 1. O que está pronto e funcionando

A tarefa da Pessoa 1 foi concluída: o dashboard não usa mais os cinco toggles manuais de contexto urbano. Agora o usuário escolhe **data e hora da gravação** e o sistema consulta sozinho os quatro fatores automáticos.

**Arquivos alterados/criados** (todos na branch `pessoa1-contexto-real`):

| Arquivo | O que mudou |
|---|---|
| `frontend/dashboard_streamlit.py` | Sidebar com data/hora + botão "Consultar contexto real"; guarda impedindo iniciar sem contexto; correção de condição de corrida ao iniciar a thread |
| `frontend/utils_dashboard.py` | `resumir_contexto()`, `coletar_avisos()`, `traduzir_avisos_contexto()` |
| `backend/analytics/contexto_tempo_real.py` | `verificar_dia_de_jogo()` agora delega para o novo calendário (assinatura preservada) |
| `backend/analytics/calendario_jogos.py` | **Novo.** Parser do calendário do Brasileirão |
| `backend/analytics/dados/brasileirao_2026.txt` | **Novo.** Cópia local do calendário (fallback offline) |
| `backend/tests/test_dashboard_utils.py` | +8 testes |
| `backend/tests/test_calendario_jogos.py` | **Novo.** 5 testes |
| `backend/tests/test_contexto_tempo_real.py` | −2 testes obsoletos (mockavam o TheSportsDB) |
| `CLAUDE.md` | Regras do projeto para agentes de código |
| `.gitignore` | Ignora os scripts de diagnóstico descartáveis |

**Suíte de testes: 58 → 69 passando.**

### Os cinco fatores, um por um

| Fator | Fonte | Status |
|---|---|---|
| 🎉 Feriado | biblioteca `holidays` (local) | Funciona, inclusive offline |
| 🕐 Horário de pico | cálculo local (dia útil, 7-9h e 17-19h) | Funciona, inclusive offline |
| 🌧️ Chuva forte | Open-Meteo (API) | Funciona **com ressalva** — ver seção 5 |
| ⚽ Dia de jogo | openfootball (domínio público) + cópia local | Funciona, inclusive offline |
| 🚧 Obra viária | toggle manual | Único manual, por decisão — não existe fonte pública |

### A prova de que a integração funciona ponta a ponta

Dois relatórios reais gerados hoje, mesmo vídeo, mesma infração, contextos diferentes:

**`backend/outputs/relatorios/infracoes_Camera_1_20260907_133754.csv`**
58 × `INVASAO_FAIXA` → causa **"Pintura desgastada / ausente"** · confiança 0.35 · `cenarios_ativos` vazio

**`backend/outputs/relatorios/infracoes_Avenida_Norte_20260907_132601.csv`**
168 × `INVASAO_FAIXA` → causa **"Sinalização pouco visível"** · confiança 0.3448 · `cenarios_ativos` = *"Chuva Forte / Baixa Visibilidade, Horário de Pico"*

O 0.3448 confere com a `TABELA_PROBABILIDADES_BASE`: base 0.25 + modificador de chuva 0.25 = 0.50, dividido pela soma 1.45 = 0.3448. **Guardem esses dois arquivos** — é a melhor evidência que temos para a apresentação.

---

## 2. Decisão técnica importante, para ninguém desfazer sem querer

O `st.session_state.contexto` é um **objeto** `GerenciadorContextoUrbano`, criado uma vez e passado **por referência** para a thread de processamento e para o `InfracaoDetector`. É ele que alimenta o `MotorCausaRaiz`.

**Nunca substituam esse objeto por um dicionário.** Para mudar o contexto, chamem `st.session_state.contexto.atualizar_contexto(...)`. Se alguém trocar o objeto por um dict, a tela continua mostrando o contexto certo e o detector passa a calcular causa-raiz com todos os fatores em `False` — sem erro, sem aviso, sem ninguém perceber até a banca.

Isso está escrito no `CLAUDE.md` da raiz, junto com as outras invariantes.

---

## 3. 🔴 Os dois problemas que podem inviabilizar a demonstração

### 3.1 Os vídeos não servem para o que o projeto se propõe

Abri o `backend/calibration/scratch_frames/cruzamento_centro.jpg` (gerado pelo próprio `validar_presets.py` do repositório). O `video_teste.mp4` é:

- Um **preview de banco de imagens com marca d'água da Shutterstock atravessando a tela**. Isso aparece na projeção durante a apresentação, e é uso de material licenciado sem licença.
- Uma **rodovia noturna americana, sem semáforo e sem faixa de pedestres no enquadramento**. Ou seja: mesmo com calibração perfeita, "avanço de sinal vermelho" e "invasão de faixa de pedestres" não têm o que detectar ali. Duas das nossas três infrações.

**O que precisa ser decidido hoje, antes de qualquer recalibração:** de onde vêm os vídeos. Critérios mínimos:

- Sem marca d'água e com licença que permita uso (Pexels e Pixabay têm material livre; gravação própria também resolve)
- **Cruzamento com semáforo visível** — senão avanço de sinal nunca dispara
- **Faixa de pedestres visível** — senão invasão de faixa não faz sentido
- Câmera parada, ângulo elevado
- 30 a 60 segundos bastam

Recalibrar 5 vídeos leva 3-4 horas. **Não gastem esse tempo em material que não serve.**

### 3.2 Os presets de calibração estão inválidos

O repositório já tem um validador pronto: `python backend\calibration\validar_presets.py`. Ele lê o `BANCO_VIDEOS.md`, imprime os problemas e gera um JPG com as zonas desenhadas sobre o vídeo, em `backend/calibration/scratch_frames/`. **Ele já foi rodado hoje e os alertas foram ignorados.**

O que encontrei abrindo os JSONs:

| Preset | Problema |
|---|---|
| `cruzamento_centro` | 23 "linhas de faixa" de ~13 pixels cada (num frame de 352×240) — cliques aleatórios, não linhas de via. **0 polígonos e 0 zonas de cruzamento**: invasão de faixa e bloqueio de cruzamento são impossíveis. As linhas de retenção estão desenhadas sobre um prédio e um estacionamento, fora da pista. |
| `invasao_faixa` | **0 linhas de retenção** — avanço de sinal nunca dispara. Um polígono de cruzamento tem pontos repetidos. |
| `avenida_norte` | O melhor dos três: 8 linhas, 2 polígonos, 2 zonas de cruzamento. Ainda assim precisa ser conferido visualmente. |

Confirmação em execução real, na janela do detector:
```
Total: 56   Sinal Verm.: 0   Faixa: 56   Bloqueio: 0
```
Só uma das três infrações dispara. Isso vai aparecer na Área 3 como um gráfico de pizza com uma fatia só de 100%, que é exatamente o que está acontecendo agora.

**Rodem o validador antes e depois de cada recalibração.** Ele existe justamente para isso.

---

## 4. 🟡 Problemas abertos de menor gravidade

### 4.1 O preview de vídeo da Área 1 não renderiza

O "Simulador de Câmera Urbana" não mostra imagem nenhuma durante o processamento. A detecção funciona normalmente — o CSV é gravado com as infrações e a causa-raiz correta —, é só a imagem na tela que não sai.

- Testado na versão atual e na versão anterior às mudanças da Pessoa 1: não aparece nas duas. **Não foi introduzido hoje.**
- Fora do Streamlit funciona: `python backend\detection\monitorar_infracoes.py --source videos_originais\video_teste.mp4 --preset avenida_norte --janela` abre a janela com o vídeo e as caixas normalmente.
- Onde olhar: `processar_video_worker` grava o frame em `state.latest_frame`; a Área 1 lê e desenha com `frame_placeholder.image(display_frame)`.

Um "Simulador de Câmera" sem imagem é ruim de apresentar. Se não der para consertar, o plano B é mostrar a detecção pela janela do `monitorar_infracoes.py` e usar o dashboard para o contexto e o diagnóstico.

### 4.2 Teste intermitente

`test_evidencias.py::test_multiplas_infracoes_simultaneas_limpam_pending` falhou uma vez e passou nas seguintes. Depende de tempo real de threads. **Não é regressão** — mas se na integração de hoje à noite alguém vir um número diferente de testes passando, é provavelmente esse. Não entrem em pânico: rodem o arquivo isolado para confirmar.

### 4.3 Lentidão do dashboard

O `st.rerun()` roda a cada frame e redesenha a página inteira, incluindo os dois gráficos Plotly da Área 3 e a leitura do CSV. Se ficar insuportável, a mudança de uma linha é aumentar o `time.sleep(0.04)` do fim da Área 1 para `0.2` — cai de ~25 para 5 redesenhos por segundo, e como os vídeos têm 5-6 fps, quase não se perde nada visualmente.

Atenção também: se alguém deixar uma janela do `monitorar_infracoes.py` aberta, são dois YOLOs disputando a mesma CPU. Fechem com **Q**.

### 4.4 Aviso de depreciação do Streamlit

Centenas de `use_container_width will be removed after 2025-12-31` no terminal. Não é erro e não quebra nada agora, mas vai quebrar numa atualização futura do Streamlit. Depois da entrega.

---

## 5. Limites reais das fontes de dados (não são bugs)

Vocês vão bater nisso e achar que quebrou. Não quebrou.

**Clima (Open-Meteo).** O endpoint de arquivo histórico tem uns 5 dias de atraso e o de previsão cobre ~16 dias à frente. **Data muito recente ou muito no futuro volta sem chuva**, silenciosamente. Para demonstrar chuva, usem data de pelo menos uma semana atrás. Existe um script na raiz, `scratch_datas_chuva.py` (fora do Git), que lista as horas em que realmente choveu forte em São Paulo num período.

**Jogos.** A integração original usava o TheSportsDB com a chave gratuita. **Testei e ela devolve sempre a mesma resposta de exemplo — 3 jogos de beisebol de 10/10/2014 — independentemente da data, do esporte e da liga.** Nunca ia confirmar um jogo real. O football-data.org também não serve: o Brasileirão não está no plano gratuito deles.

A fonte agora é o **openfootball**, dados de futebol em domínio público no GitHub, sem chave de API, com o Brasileirão 2026 completo até a rodada mais recente. Há cópia local commitada, então o fator funciona mesmo sem internet.

Isso vale ser contado na apresentação em vez de escondido: integramos uma API de agenda esportiva, descobrimos em teste que a chave gratuita devolvia dados de exemplo, e migramos para uma base de domínio público com contingência offline. É uma história de engenharia melhor do que "integramos uma API".

---

## 6. Datas validadas para a demonstração

| Data e hora | Fatores que acendem | Observação |
|---|---|---|
| `29/07/2026 18:00` | 🌧️ Chuva forte (3.6 mm/h) + 🕐 Pico | Quarta-feira. Testado, funciona. |
| `25/12/2026 18:00` | 🎉 Feriado + 🕐 Pico | Sexta-feira. Sem chuva (data futura demais para a API). |
| `04/02/2026 18:00` | ⚽ Santos FC x São Paulo FC + 🕐 Pico | Quarta-feira. Testado, funciona. |
| Qualquer uma acima + toggle 🚧 | Três fatores | O jeito honesto de mostrar o efeito máximo |

Para o contraste de causa-raiz, usem `15/07/2026 14:00` — quarta à tarde, nenhum fator ativo.

---

## 7. O que falta para entregar

### Caminho crítico (bloqueia tudo)

- [ ] **Decidir os vídeos** — com semáforo e faixa de pedestres visíveis, sem marca d'água, licença livre. Sem isso, recalibrar é desperdício.
- [ ] **Recalibrar do zero** os presets dos vídeos escolhidos, com `calibrar_camera.py`. Linha de retenção **e** linha de faixa em posições diferentes, mais polígono de faixa de pedestres e zona de cruzamento.
- [ ] **Rodar `validar_presets.py`** e **abrir os JPGs gerados** depois de cada calibração. Não confiar só na ausência de erro.
- [ ] **Atualizar o `BANCO_VIDEOS.md`** com os vídeos e presets finais.

### Integração

- [ ] `git pull` da branch `pessoa1-contexto-real` e merge
- [ ] Conectar a seleção de vídeo ao preset correto automaticamente (`VIDEO_PRESET_MAP`), tarefa da Pessoa 3
- [ ] Confirmar que o upload de vídeo próprio ainda funciona
- [ ] `python -m pytest backend\tests\ -v` com tudo integrado — esperado 69 ou mais

### Validação final, com o grupo reunido

- [ ] Teste ponta a ponta em pelo menos 2 vídeos: escolher vídeo → escolher data/hora → consultar contexto → iniciar → ver infração com causa-raiz → conferir a Área 3
- [ ] Confirmar que **as três infrações** disparam em algum vídeo do banco (hoje só uma dispara)
- [ ] Ensaio cronometrado da apresentação, decidindo quem fala o quê

### Se sobrar tempo

- [ ] Consertar o preview de vídeo da Área 1
- [ ] Modo exploratório para vídeo enviado sem preset, com aviso claro de precisão menor

---

## 8. Armadilhas — leiam antes de usar o Git

**Nunca rodem `git add .` neste repositório.** Há dois arquivos `.zip` na raiz somando 277 MB (`.github.zip` e `zip2.zip`). O GitHub rejeita arquivo acima de 100 MB, e vocês ficariam com um commit impossível de empurrar, tendo que reescrever o histórico. Adicionem `*.zip` ao `.gitignore` e apaguem os dois — foram criados só para transferir a pasta e não servem para mais nada.

**O `backend/analytics/dados/brasileirao_2026.txt` precisa estar commitado.** É a cópia local do calendário. Sem ele, o fallback offline não existe nas outras máquinas e o teste que simula queda de rede falha.

**Caminho da pasta no PowerShell sempre entre aspas.** O nome tem um travessão e espaços; sem aspas o `cd` falha com erro de parâmetro.

**Use `python -m`** para tudo (`python -m pytest`, `python -m streamlit`, `python -m pip`). O diretório `Scripts` do Python não está no PATH desta máquina, então `streamlit run` direto não funciona.

---

## 9. Comandos úteis

```powershell
# Sempre da raiz do projeto, com aspas
cd "C:\Users\<usuario>\...\Área de Trabalho\COGNIMOVE"

# Testes
python -m pytest backend\tests\ -v

# Dashboard
python -m streamlit run frontend/dashboard_streamlit.py

# Detector fora do Streamlit (o vídeo aparece aqui)
python backend\detection\monitorar_infracoes.py --source videos_originais\<video> --preset <preset> --janela

# Calibrar
python backend\calibration\calibrar_camera.py --source videos_originais\<video> --preset <nome>

# Validar os presets e gerar os JPGs de conferência
python backend\calibration\validar_presets.py

# Conferir a causa-raiz respondendo ao contexto, sem rodar vídeo
python -c "from backend.analytics.causa_raiz import MotorCausaRaiz; from backend.analytics.contexto_urbano import GerenciadorContextoUrbano; g=GerenciadorContextoUrbano(); m=MotorCausaRaiz(); print('sem contexto ->', m.calcular_probabilidades('INVASAO_FAIXA', g.obter_contexto_atual())['causa_principal']); g.atualizar_contexto(chuva_forte=True, horario_pico=True); print('com chuva+pico ->', m.calcular_probabilidades('INVASAO_FAIXA', g.obter_contexto_atual())['causa_principal'])"
```

---

## 10. Resumo em três linhas

O contexto urbano real está funcionando e provado por dois relatórios com causas-raiz diferentes. O que ameaça a entrega não é código: são os vídeos (marca d'água, e sem semáforo nem faixa de pedestres) e a calibração (rabiscada, com duas das três infrações impossíveis de detectar). Decidam os vídeos primeiro — recalibrar antes disso é jogar 4 horas fora.
