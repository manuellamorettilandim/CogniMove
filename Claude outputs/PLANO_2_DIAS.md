# CogniMove — Plano até 10/09

**Quem:** Manu (backend/contexto) e Melissa (calibração). Raíssa entra depois, no frontend.
**Prazo:** 10/09 — dois dias.
**Estado:** contexto urbano real pronto e empurrado na branch `pessoa1-contexto-real`. Vídeos novos adicionados. Calibração pendente.

O caminho crítico é a **calibração**. Tudo que a Manu fizer é para não travar a Melissa e para cobrir o que a Raíssa ainda não pode fazer.

---

## Bloco 0 — Sincronizar (as duas juntas, 30 min, faça agora)

Enquanto a branch não for mesclada, vocês estão trabalhando em versões diferentes do `dashboard_streamlit.py`. Isso só piora com o tempo.

**Manu:**

```powershell
git fetch origin
git log --oneline origin/main -5
git log --oneline origin/pessoa1-contexto-real -3
```

Vejam se a `main` andou desde o push. Depois:

```powershell
git checkout main
git pull origin main
git merge origin/pessoa1-contexto-real
python -m pytest backend\tests\ -q     # tem que dar 69
git push origin main
```

Se der conflito no `dashboard_streamlit.py`, resolvam com o `CLAUDE.md` da raiz aberto ao lado. A regra que não pode ser quebrada: `st.session_state.contexto` continua sendo o **objeto** `GerenciadorContextoUrbano`, alimentado por `atualizar_contexto(...)`. Se virar dicionário, a tela mostra o contexto certo e o detector calcula causa-raiz com tudo em `False`, sem erro nenhum.

**Melissa, depois que a Manu empurrar:**

```powershell
git checkout main
git pull origin main
python -m pytest backend\tests\ -q     # 69, o mesmo número
```

**Confirmem no grupo que as duas veem 69.** A partir daqui, ninguém mais cria branch: trabalhem direto na `main`, avisando antes de cada push.

**Manu, aproveite e limpe:** os arquivos `.github.zip` e `zip2.zip` (277 MB juntos) ainda estão na raiz. Apague os dois e acrescente `*.zip` ao `.gitignore`. Se alguém rodar `git add .` com eles ali, o push falha e vocês perdem tempo reescrevendo histórico.

---

## Bloco 1 — Hoje, em paralelo

### Melissa — calibrar (3-4h, é o caminho crítico)

Na minha máquina só aparecem três vídeos em `videos_originais/` (`video_teste.mp4`, `2` e `3`). **Empurre os novos** para que a Manu consiga testar:

```powershell
git add videos_originais/
git status
git commit -m "feat(videos): adiciona videos novos para o banco de demonstracao"
git push origin main
```

Antes de calibrar, **descarte os presets antigos dos vídeos que mudaram**. Eles estão rabiscados e é mais rápido refazer do que corrigir — o `cruzamento_centro` tem 23 linhas de 13 pixels desenhadas em cima de um prédio.

Para cada vídeo:

```powershell
python backend\calibration\calibrar_camera.py --source videos_originais\<video> --preset <nome_descritivo>
```

**Critérios de pronto para cada preset** (é isso que faltou da última vez):

- **1 linha de retenção** (`R`), atravessando a via, um pouco antes do cruzamento — onde os carros param no vermelho
- **1 linha de faixa/limite** (`L`), **em posição diferente da de retenção**. Desenhar as duas no mesmo lugar já foi um bug real do projeto
- **1 polígono de faixa de pedestres** (`P`), com 4 pontos ou mais, fechado com clique direito
- **1 polígono de zona de cruzamento**, também 4+ pontos
- **Cada linha precisa ter pelo menos 5% da largura da imagem.** Num vídeo de 352 px, são ~18 px. Traços curtinhos não valem
- Poucas formas e bem colocadas. Não é para acumular linha

Depois de cada vídeo:

```powershell
python backend\detection\monitorar_infracoes.py --source videos_originais\<video> --preset <preset> --janela
```

Confira na janela: as linhas e polígonos estão alinhados com a rua de verdade? Os carros ganham caixa? Alguma infração dispara?

Quando os quatro estiverem prontos:

```powershell
python backend\calibration\validar_presets.py
```

**E abra os JPGs que ele gera** em `backend/calibration/scratch_frames/`. Não basta o script não reclamar — é para olhar a imagem e ver as zonas em cima da rua. Da última vez os JPGs foram gerados e ninguém abriu.

Por último, atualize `backend/calibration/presets/BANCO_VIDEOS.md` com vídeo, preset e uma frase sobre o que cada um demonstra bem.

### Manu — consertar o preview da Área 1 (2h, com hora para acabar)

O "Simulador de Câmera Urbana" não mostra imagem durante o processamento. A detecção funciona (o CSV sai correto), mas a tela fica vazia. Num projeto de detecção visual, apresentar isso sem imagem é ruim.

Onde olhar: `processar_video_worker` grava o frame em `state.latest_frame`; a Área 1 lê e desenha com `frame_placeholder.image(display_frame)`. A condição de corrida ao iniciar já foi corrigida, então agora um `st.error` consegue aparecer — rode uma vez e veja se algum erro surge.

**Prazo firme: 2 horas.** Se não sair, para, anota o que descobriu e deixa para a Raíssa. O plano B da apresentação é mostrar a detecção pela janela do `monitorar_infracoes.py --janela`, que funciona bem, e usar o dashboard para o contexto e o diagnóstico. Não é o ideal, mas não é fracasso.

Se sobrar tempo depois disso, a lentidão tem um paliativo de uma linha: no fim da Área 1, trocar `time.sleep(0.04)` por `0.2` antes do `st.rerun()`. Cai de ~25 para 5 redesenhos por segundo, e como os vídeos têm 5-6 fps, quase não se perde nada.

---

## Bloco 2 — Hoje à noite, as duas juntas (1h)

### O teste que ainda não foi feito: as três infrações

Hoje só `INVASAO_FAIXA` dispara. Numa execução real o detector mostrou `Sinal Verm.: 0 | Faixa: 56 | Bloqueio: 0`, e a Área 3 vira um gráfico de pizza com uma fatia só de 100%.

Rodem os vídeos calibrados e confiram que, **somando o banco todo**, as três infrações aparecem pelo menos uma vez:

- `AVANCO_SINAL_VERMELHO` — precisa de linha de retenção **e** de semáforo visível no vídeo
- `INVASAO_FAIXA` — precisa da linha de faixa e do polígono de pedestres
- `BLOQUEIO_CRUZAMENTO` — precisa do polígono de zona de cruzamento

Se alguma não aparecer em nenhum vídeo, **decidam hoje** se dá para resolver com calibração ou se vão apresentar duas das três e explicar por quê. Descobrir isso na hora da apresentação é o pior cenário.

### Teste ponta a ponta

Com pelo menos 2 vídeos, uma compartilhando a tela:

1. Escolher vídeo
2. Escolher data e hora → **Consultar contexto real**
3. Conferir que os fatores certos acendem
4. Iniciar monitoramento → esperar a infração
5. Conferir a causa-raiz no alerta
6. Conferir os gráficos da Área 3

**Datas já validadas:**

| Data e hora | Fatores | Para quê |
|---|---|---|
| `29/07/2026 18:00` | 🌧️ Chuva (3.6 mm/h) + 🕐 Pico | Caso principal |
| `04/02/2026 18:00` | ⚽ Santos x São Paulo + 🕐 Pico | Mostra o calendário de jogos |
| `25/12/2026 18:00` | 🎉 Feriado + 🕐 Pico | Mostra a fonte de feriados |
| `15/07/2026 14:00` | nenhum | O contraste, para comparar a causa-raiz |

Qualquer uma delas + o toggle 🚧 dá três fatores.

---

## Bloco 3 — Dia 09

### Manhã: fechar as pontas

- [ ] Ligar seleção de vídeo ao preset automaticamente (`VIDEO_PRESET_MAP` no `dashboard_streamlit.py`) — hoje o usuário escolhe os dois separado, e na demonstração isso dá erro humano
- [ ] Testar o upload de vídeo próprio, confirmando que não quebra
- [ ] `python -m pytest backend\tests\ -q` com tudo integrado

### Tarde: ensaio

Rodem a apresentação inteira, cronometrando, decidindo quem fala o quê. Roteiro sugerido:

1. **O problema** — multas punem, não diagnosticam
2. **Detecção** — vídeo real, YOLO, as infrações aparecendo
3. **Contexto** — escolher `29/07/2026 18:00`, mostrar o sistema descobrindo chuva e pico sozinho pela data
4. **Causa-raiz** — a mesma infração com diagnóstico diferente conforme o contexto. Mostrem os dois CSVs: 58 infrações → *"Pintura desgastada / ausente"*; 168 infrações com chuva e pico → *"Sinalização pouco visível"*
5. **Recomendação** — a Área 3 e a intervenção sugerida

O passo 4 é o coração do projeto. É ele que separa "detector de infração" de "ferramenta de diagnóstico urbano".

### Preparem as respostas difíceis

- **"A previsão do tempo funciona para qualquer data?"** Não. O arquivo histórico tem ~5 dias de atraso e a previsão cobre ~16 dias. Fora dessa janela o sistema assume sem chuva e avisa na interface.
- **"E se a API cair?"** Todos os fatores têm fallback. Feriado e horário de pico são calculados localmente; o calendário de jogos tem cópia local no repositório; o clima avisa e assume sem chuva. Demonstrem desligando o Wi-Fi.
- **"De onde vêm os dados de jogos?"** Do openfootball, base de domínio público. E contem a história: começamos com o TheSportsDB, descobrimos em teste que a chave gratuita devolvia sempre a mesma resposta de exemplo — três jogos de beisebol de 2014 — e migramos. Isso conta a favor de vocês, não contra.
- **"Por que obra viária é manual?"** Porque não existe fonte pública automatizável. Foi decisão consciente, está documentada.

---

## Bloco 4 — Dia 10, manhã

- [ ] `git pull` final, `pytest` verde nas duas máquinas
- [ ] Uma execução completa sem tocar em código
- [ ] **Congelar.** Nada de "só mais um ajuste" — é assim que se chega quebrado na apresentação
- [ ] Deixar o `monitorar_infracoes.py --janela` pronto como plano B, caso o preview da Área 1 não tenha sido resolvido

---

## Divisão rápida

| | Manu | Melissa |
|---|---|---|
| **Hoje** | Merge, limpeza dos zips, preview da Área 1 (2h no máximo) | Empurrar vídeos novos, recalibrar tudo, validar, `BANCO_VIDEOS.md` |
| **Noite** | Teste ponta a ponta, juntas | Teste ponta a ponta, juntas |
| **Dia 09** | `VIDEO_PRESET_MAP`, upload, testes | Conferir os presets no dashboard, ensaio |
| **Dia 10** | Congelar e ensaiar | Congelar e ensaiar |

---

## Regras de convivência no Git

- Todo mundo na `main`. Avisar no grupo antes de cada push
- `git pull` antes de começar a mexer, sempre
- **Nunca `git add .`** — listar os arquivos um a um
- Vídeos são pesados (40-64 MB cada). Se o banco crescer muito, considerem manter os vídeos fora do Git e compartilhar por drive, deixando no repositório só os presets. Se já estão commitados, deixem como está — trocar isso na véspera não vale o risco
- Antes de qualquer push: `python -m pytest backend\tests\ -q`

---

## Se o tempo apertar, corte nesta ordem

1. Preview da Área 1 (existe plano B)
2. Modo exploratório para vídeo enviado sem preset
3. Reduzir o banco de 5 para 3 vídeos bem calibrados

**O que não pode ser cortado:** as três infrações aparecendo em algum vídeo, e a demonstração da causa-raiz mudando com o contexto. Sem esses dois, o projeto não mostra o que se propõe a mostrar.
