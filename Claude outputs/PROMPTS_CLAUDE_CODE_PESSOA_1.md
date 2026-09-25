# Prompts para o Claude Code — Pessoa 1 (CogniMove)

Um prompt por passo do `PLANO_PESSOA_1.md`. Copie e cole o bloco inteiro, um de cada vez, **na ordem**, e confira o resultado antes de passar para o próximo.

**Três regras que valem para todos:**

1. Abra o Claude Code **na raiz do projeto** (`.../Área de Trabalho/COGNIMOVE`), não numa subpasta.
2. Não peça para ele rodar `streamlit run` — é um processo que não termina e trava a sessão. Os testes visuais são teus, na mão.
3. Depois de cada prompt, rode `git diff` e leia o que mudou. São ~5 minutos que evitam a noite inteira de debug.

---

## Prompt 0 — Preparar o terreno (rode uma vez só)

Este cria um `CLAUDE.md` com as regras do projeto. Todos os prompts seguintes herdam esse contexto, o que deixa cada um deles mais curto e reduz a chance de o Claude Code inventar coisa.

```
Leia estes arquivos, sem editar nada ainda:
- frontend/dashboard_streamlit.py
- backend/analytics/contexto_tempo_real.py
- backend/analytics/contexto_urbano.py
- backend/analytics/causa_raiz.py
- frontend/utils_dashboard.py
- backend/tests/test_dashboard_utils.py

Depois crie um arquivo CLAUDE.md na raiz do projeto com este conteúdo exato:

# CogniMove — Regras para o agente

## Contexto da tarefa atual
Estou substituindo os toggles manuais de contexto urbano do dashboard Streamlit
por consulta automática a APIs reais (clima, feriados, jogos) a partir de uma
data/hora escolhida pelo usuário.

## Invariantes que NÃO podem ser quebradas
- `st.session_state.contexto` é um objeto `GerenciadorContextoUrbano`, criado uma
  única vez. Ele é passado POR REFERÊNCIA para a thread de processamento
  (`processar_video_worker`) e para `InfracaoDetector(contexto_urbano=...)`, e é
  a fonte que alimenta `MotorCausaRaiz.calcular_probabilidades()`.
  NUNCA substitua esse objeto por um dicionário. Para mudar o contexto, chame
  `st.session_state.contexto.atualizar_contexto(...)`.
- O dashboard tem um `st.rerun()` em loop enquanto processa vídeo: o script
  re-executa dezenas de vezes por segundo. Nenhuma chamada de rede pode ficar
  solta no corpo do script — só dentro de um `if st.button(...)`, com o
  resultado guardado em `st.session_state`.
- `construir_contexto_a_partir_de_data()` já trata todas as falhas de rede
  internamente e devolve fallback `False`. Não reimplemente esse tratamento.

## Convenções
- Imports do dashboard usam o prefixo curto: `from analytics.x import y`
  (o sys.path é montado nas primeiras linhas do arquivo). Não use `backend.` lá.
- Testes ficam em `backend/tests/` e importam com `from frontend.x import y`.
- Comentários e docstrings em português.

## O que você NÃO deve fazer
- Não rode `streamlit run` (processo que não termina).
- Não faça `git commit` nem `git push` sem eu pedir explicitamente.
- Não refatore, reformate nem "melhore" código fora do escopo pedido.
- Não crie arquivos novos que eu não pedi.

Não altere nenhum outro arquivo neste passo.
```

---

## Prompt 1 — Checagem de ambiente e verificação de fumaça

```
Sem editar nenhum arquivo, faça o diagnóstico do ambiente e me devolva um relatório curto:

1. Rode `git status` e `git branch --show-current`. Me diga se há alterações não commitadas.
2. Verifique se as dependências estão instaladas:
   python -c "import holidays, requests, streamlit; print('ok')"
   Se `holidays` faltar, me avise (não instale sem eu pedir).
3. Rode `python -m pytest backend/tests/ -q` e me diga o número exato de testes que passaram.
   Esse número é o meu piso para o resto do dia.
4. Verificação de fumaça da função que vou integrar — rode da raiz do projeto:
   python -c "import datetime; from backend.analytics.contexto_tempo_real import construir_contexto_a_partir_de_data as f; print(f(datetime.date(2026,12,25), datetime.time(18,0)))"
   Me mostre a saída literal. Eu espero ver 'feriado': True e 'horario_pico': True.
   Se der erro de import ou de rede, me diga qual foi e NÃO tente contornar
   alterando o código — quero saber do problema, não escondê-lo.

Me responda em no máximo 10 linhas. Não crie branch, não commite.
```

Depois que ele responder, crie a branch você mesmo (é rápido e você fica com o controle):

```powershell
git checkout -b pessoa1-contexto-real
```

---

## Prompt 2 — `resumir_contexto()` + testes

```
Tarefa: adicionar uma função de formatação testável e cobri-la com testes.

ARQUIVO 1 — frontend/utils_dashboard.py
Acrescente ao FINAL do arquivo, sem alterar a função existente
`obter_causa_predominante`, exatamente esta função:

def resumir_contexto(contexto: dict | None) -> str:
    """Monta a frase legível com os fatores urbanos ativos de um contexto.

    Recebe o dict devolvido por `construir_contexto_a_partir_de_data` e
    devolve algo como:
        "🌧️ Chuva forte (4.2 mm/h) — 🕐 Horário de pico — 🎉 Feriado"
    """
    if not contexto:
        return "Contexto ainda não consultado."

    detalhes = contexto.get("_detalhes") or {}
    partes: list[str] = []

    if contexto.get("chuva_forte"):
        mm = detalhes.get("precipitacao_mm") or 0.0
        partes.append(f"🌧️ Chuva forte ({mm:.1f} mm/h)")
    if contexto.get("horario_pico"):
        partes.append("🕐 Horário de pico")
    if contexto.get("dia_jogo"):
        partes.append(f"⚽ {detalhes.get('confronto') or 'Jogo na cidade'}")
    if contexto.get("feriado"):
        partes.append("🎉 Feriado")
    if contexto.get("obra_viaria"):
        partes.append("🚧 Obra viária")

    return " — ".join(partes) if partes else "Nenhum fator de risco identificado."

ARQUIVO 2 — backend/tests/test_dashboard_utils.py
Acrescente ao FINAL do arquivo quatro testes para essa função, seguindo o estilo
dos testes que já estão lá (docstring curta em português explicando o cenário).
Ajuste a linha de import existente para trazer também `resumir_contexto`.
Os quatro cenários que quero cobertos:
  a) contexto None devolve "Contexto ainda não consultado."
  b) todos os fatores False devolve "Nenhum fator de risco identificado."
  c) chuva + jogo + pico ativos: a frase contém "4.2 mm/h", o nome do confronto e
     "Horário de pico", e NÃO contém "Feriado"
  d) dict sem a chave "_detalhes" não quebra: devolve "0.0 mm/h" e "Jogo na cidade"

VERIFICAÇÃO
Rode `python -m pytest backend/tests/test_dashboard_utils.py -v` e me mostre o
resultado. Depois rode a suíte inteira e confirme que o total subiu em 4.

Não toque em frontend/dashboard_streamlit.py neste passo. Não commite.
```

---

## Prompt 3 — Editar a sidebar do dashboard (o passo crítico)

> Este é o prompt mais importante. Ele traz o código inteiro pronto justamente para o Claude Code **não** precisar inventar nada. Depois de rodar, leia o `git diff` com atenção.

```
Tarefa: em frontend/dashboard_streamlit.py, substituir os toggles manuais de
contexto urbano por consulta automática a partir de data/hora.

MUDANÇA 1 — imports
No bloco de imports do projeto (as linhas que começam com
`from analytics.contexto_urbano import ...`), faça exatamente duas alterações:
  - adicione: from analytics.contexto_tempo_real import construir_contexto_a_partir_de_data
  - na linha do utils_dashboard, importe também `resumir_contexto`
`import datetime` JÁ EXISTE no topo do arquivo — não adicione de novo.

MUDANÇA 2 — substituir o bloco da sidebar
Localize, dentro do `with st.sidebar:`, o bloco que começa em
    st.markdown("## 🌧️ Fatores Urbanos (Módulo 3)")
e termina logo antes de
    st.divider()
    usar_ia = st.checkbox("⚡ Processar com Modelo de IA ...
Esse bloco inclui os cinco `st.toggle` (chk_chuva, chk_jogo, chk_pico,
chk_feriado, chk_obra), a chamada `atualizar_contexto(...)` que vem deles, e a
seção "### 📊 Status do Ambiente:".
Apague TODO esse bloco e coloque no lugar, mantendo a indentação de 4 espaços do
`with st.sidebar:`:

    st.markdown("## 📅 Contexto da Gravação (Módulo 3)")
    st.caption(
        "Informe quando este vídeo foi gravado. O CogniMove consulta feriados, "
        "clima e agenda esportiva reais para essa data e hora."
    )

    col_data, col_hora = st.columns(2)
    with col_data:
        data_gravacao = st.date_input(
            "Data da gravação",
            value=datetime.date(2026, 12, 25),
            format="DD/MM/YYYY",
            key="data_gravacao",
        )
    with col_hora:
        hora_gravacao = st.time_input(
            "Horário da gravação",
            value=datetime.time(18, 0),
            key="hora_gravacao",
        )

    obra_viaria = st.toggle(
        "🚧 Obra viária no local",
        key="toggle_obra",
        help="Único fator sem fonte pública automatizável — informe manualmente.",
    )

    if st.button("🔍 Consultar contexto real", use_container_width=True, type="primary"):
        with st.spinner("Consultando feriados, clima e jogos..."):
            try:
                st.session_state.contexto_dados = construir_contexto_a_partir_de_data(
                    data_gravacao, hora_gravacao, obra_viaria_manual=obra_viaria
                )
                st.session_state.contexto_erro = None
            except Exception as e:
                st.session_state.contexto_dados = None
                st.session_state.contexto_erro = str(e)

    if st.session_state.get("contexto_erro"):
        st.warning(
            "Não foi possível consultar todas as fontes externas "
            f"({st.session_state.contexto_erro}). Fatores não confirmados serão "
            "considerados inativos."
        )

    dados_ctx = st.session_state.get("contexto_dados")

    if dados_ctx:
        # O toggle de obra é manual e vale imediatamente, sem nova consulta de rede.
        dados_ctx["obra_viaria"] = obra_viaria

        # Reaplica as flags no gerenciador a cada rerun. É barato (não usa rede) e
        # garante que o detector e o MotorCausaRaiz enxerguem sempre o contexto atual,
        # já que o objeto é passado por referência para a thread de processamento.
        st.session_state.contexto.atualizar_contexto(
            chuva_forte=dados_ctx.get("chuva_forte", False),
            dia_jogo=dados_ctx.get("dia_jogo", False),
            horario_pico=dados_ctx.get("horario_pico", False),
            feriado=dados_ctx.get("feriado", False),
            obra_viaria=obra_viaria,
        )

    st.markdown("---")
    st.markdown("### 📊 Status do Ambiente")

    if dados_ctx:
        DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
                "Sexta-feira", "Sábado", "Domingo"]
        cabecalho = (
            f"📅 {DIAS[data_gravacao.weekday()]}, "
            f"{data_gravacao.strftime('%d/%m/%Y')} às {hora_gravacao.strftime('%H:%M')}"
        )
        st.info(f"**{cabecalho}**\n\n{resumir_contexto(dados_ctx)}")
    else:
        st.caption("Clique em **Consultar contexto real** para carregar o contexto desta gravação.")

RESTRIÇÕES
- Não altere mais NADA no arquivo: nem o CSS, nem o worker, nem as Áreas 1 e 3,
  nem a seleção de vídeo/preset (essa parte é de outra pessoa da equipe).
- Não substitua `st.session_state.contexto` por um dicionário em lugar nenhum.

VERIFICAÇÃO — me responda com estes 4 itens:
1. `python -m py_compile frontend/dashboard_streamlit.py` passou?
2. Rode `grep -n "chk_chuva\|chk_jogo\|chk_pico\|chk_feriado\|chk_obra" frontend/dashboard_streamlit.py`
   e me mostre a saída. Tem que vir vazia.
3. Rode `grep -n "st.session_state.contexto" frontend/dashboard_streamlit.py` e me
   mostre as linhas, para eu confirmar que o objeto continua sendo usado no worker
   e no cálculo de causa-raiz.
4. `python -m pytest backend/tests/ -q` — mesmo número do passo anterior?

Não commite.
```

---

## Prompt 4 — Guarda do botão "Iniciar" + docstring

```
Duas alterações pequenas em frontend/dashboard_streamlit.py.

MUDANÇA 1 — impedir iniciar o monitoramento sem contexto consultado
Localize o comentário
    # Ação de iniciar: dispara worker em thread dedicada (se não houver outra ativa)
seguido de
    if iniciar and video_escolhido:
Insira ANTES desse comentário, na mesma indentação (4 espaços, dentro do
`with col_camera:`), este bloco:

    if iniciar and not st.session_state.get("contexto_dados"):
        st.warning("⚠️ Consulte o contexto da gravação (barra lateral) antes de iniciar o monitoramento.")
        iniciar = False

Não reindente nem altere o `if iniciar and video_escolhido:` que vem depois —
a variável `iniciar` vira False e o bloco existente simplesmente não executa.

MUDANÇA 2 — docstring do módulo
No docstring do topo do arquivo, substitua a linha
  Área 2: Simulador de Cenários Urbanos (Fatores externos: Chuva, Jogo, Horário de Pico, Feriado, Obras)
por
  Área 2: Contexto Urbano Real (fatores obtidos por data/hora via APIs de clima,
          feriados e agenda esportiva; obra viária informada manualmente)

VERIFICAÇÃO
`python -m py_compile frontend/dashboard_streamlit.py` e depois
`python -m pytest backend/tests/ -q`. Me mostre o `git diff` deste passo.
Não commite.
```

---

## Prompt 5 — Script auxiliar para achar datas de demonstração

```
Crie o arquivo scratch_datas_chuva.py na raiz do projeto. Ele é uma ferramenta
descartável de apoio à demonstração, não faz parte do sistema.

Objetivo: listar as horas em que realmente choveu forte em São Paulo, para eu
escolher uma data boa para a apresentação.

Requisitos:
- Consulta https://archive-api.open-meteo.com/v1/archive com
  latitude=-23.55, longitude=-46.63, hourly=precipitation,
  timezone=America/Sao_Paulo, no período de 2026-05-01 a 2026-08-31.
- Filtra as horas com precipitação >= 2.5 mm (o mesmo limiar usado em
  backend/analytics/contexto_tempo_real.py).
- Ordena da maior precipitação para a menor e imprime as 15 primeiras, cada linha
  com: data no formato DD/MM/AAAA, hora, dia da semana em português e o valor em mm/h.
- Marca com ">>> BOM PARA DEMO" as linhas que forem dia de semana (segunda a sexta)
  e horário entre 07:00-09:00 ou 17:00-19:00, porque nessas eu demonstro chuva
  E horário de pico ao mesmo tempo.
- Trata falha de rede com uma mensagem clara em vez de traceback.

Acrescente `scratch_datas_chuva.py` ao .gitignore — não quero esse arquivo no
repositório.

Depois execute o script e me mostre a saída.
```

---

## Prompt 6 — Revisão final antes do commit

> Este é o que mais paga o investimento. Ele pede uma revisão adversarial do próprio trabalho.

```
Revise criticamente todas as alterações que fizemos hoje, como se você fosse
outra pessoa procurando defeito nelas. Rode `git diff` e responda ponto a ponto:

1. Alguma chamada de rede ficou fora de um `if st.button(...)`? (o dashboard
   re-executa dezenas de vezes por segundo durante o processamento de vídeo)
2. `st.session_state.contexto` continua sendo o objeto GerenciadorContextoUrbano
   em todos os pontos de uso — sidebar, thread do worker, InfracaoDetector e o
   cálculo de causa-raiz no alerta de infração?
3. Existe algum caminho em que `dados_ctx` seja None e o código tente acessar
   uma chave dele mesmo assim?
4. Sobrou alguma referência às variáveis removidas (chk_*) ou às chaves de
   session_state antigas (toggle_chuva, toggle_jogo, toggle_pico, toggle_feriado)?
5. Alguma linha foi alterada fora do escopo (CSS, Áreas 1 e 3, seleção de
   vídeo/preset, worker)? Se sim, reverta essa parte.
6. Rode `python -m pytest backend/tests/ -v` e confirme o total.

Se encontrar problema, conserte e me diga exatamente o que era.
Se não encontrar nada, diga isso explicitamente — não invente correção.
```

---

## Prompt 7 — Commit

> Só rode depois de você ter testado o dashboard **na mão** (o roteiro de 7 testes manuais do Passo 5 do plano). O Claude Code não consegue validar isso por você.

```
Faça o commit das alterações de hoje.

Inclua apenas:
- frontend/dashboard_streamlit.py
- frontend/utils_dashboard.py
- backend/tests/test_dashboard_utils.py
- CLAUDE.md
- .gitignore (se foi alterado)

NÃO inclua: scratch_datas_chuva.py, arquivos de backend/outputs/, __pycache__,
.pytest_cache, nem qualquer vídeo.

Antes de commitar, rode `git status` e me mostre o que será incluído, para eu
confirmar. Rode `python -m pytest backend/tests/ -q` uma última vez.

Mensagem do commit:
feat(dashboard): substitui toggles manuais por contexto urbano real via data/hora

Não faça push — eu empurro depois de avisar o grupo.
```

---

## O que fazer entre o Prompt 4 e o Prompt 6

Esta parte é tua, o Claude Code não substitui. Com `streamlit run frontend/dashboard_streamlit.py` aberto:

| # | Teste | Esperado |
|---|---|---|
| 1 | `25/12/2026` às `18:00` → Consultar | 🎉 Feriado **e** 🕐 Horário de pico |
| 2 | Um sábado às `08:00` → Consultar | Sem horário de pico |
| 3 | Terça comum às `08:00` → Consultar | 🕐 Horário de pico, sem feriado |
| 4 | Ligar o toggle 🚧 Obra viária | Resumo atualiza na hora, sem reconsultar |
| 5 | Desligar o Wi-Fi → Consultar | Aviso discreto, sem tela de erro do Streamlit |
| 6 | Iniciar Monitoramento sem consultar | Aviso amarelo, vídeo não começa |
| 7 | Consultar com 2 fatores → Iniciar → esperar infração | Causa-raiz **diferente** da que aparece sem contexto |

O teste 7 é o que prova que a entrega funcionou. Se a causa-raiz for igual com e sem contexto, volte ao Prompt 6 e cole o resultado: o objeto não está sendo alimentado.

---

## Se o Claude Code se perder no meio

Sintomas de que vale interromper e recomeçar: ele começou a editar arquivos que você não pediu, ficou tentando rodar `streamlit`, ou "consertou" um teste mudando a asserção em vez do código.

Prompt de resgate:

```
Pare. Rode `git diff` e me mostre TUDO que foi alterado até agora.
Não faça mais nenhuma edição até eu responder.
```

E, se precisar voltar do zero num arquivo específico:

```powershell
git checkout -- frontend/dashboard_streamlit.py
```
