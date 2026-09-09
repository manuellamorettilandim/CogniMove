# Plano de Implementação — Pessoa 1 (Backend / Contexto Real no Dashboard)

**Projeto:** CogniMove
**Arquivo principal que você vai editar:** `frontend/dashboard_streamlit.py`
**Tempo estimado:** 2h30 a 3h (incluindo testes)

Este plano foi escrito depois de ler o teu código de verdade — não é genérico. Os números de linha abaixo se referem ao estado atual dos arquivos na tua máquina.

---

## 1. O que você tem que entregar, em uma frase

Hoje o usuário liga cinco interruptores na mão dizendo "finja que está chovendo, finja que é feriado". Você vai trocar isso por: **o usuário escolhe uma data e uma hora, e o sistema descobre sozinho** se naquele dia choveu, se era feriado, se tinha jogo e se era horário de pico — consultando APIs reais. Só "obra viária" continua manual, porque não existe fonte pública para isso.

---

## 2. Como o código funciona hoje (leia isto antes de tocar em qualquer coisa)

Esta é a parte mais importante do documento. Se você entender esse fluxo, o resto é digitação.

### 2.1 O contexto é um **objeto**, não um dicionário

Em `dashboard_streamlit.py`, linha 276-277:

```python
if "contexto" not in st.session_state:
    st.session_state.contexto = GerenciadorContextoUrbano()
```

Esse objeto (`GerenciadorContextoUrbano`) é criado uma vez e vive na sessão. Ele guarda cinco flags booleanas por dentro e é **thread-safe** (tem um `threading.Lock`). Isso importa porque ele é usado em três lugares diferentes:

| Onde | Linha | O que faz |
|---|---|---|
| Sidebar | 402-408 | Os toggles chamam `atualizar_contexto(...)` e gravam as flags dentro do objeto |
| Thread do worker | 471 | O **objeto** é passado para `processar_video_worker(...)` |
| Detector de IA | 188 | O **objeto** vai para `InfracaoDetector(contexto_urbano=contexto)` |
| Alerta de infração | 510-511 | `ctx = st.session_state.contexto.obter_contexto_atual()` → alimenta `MotorCausaRaiz.calcular_probabilidades(...)` |

Ou seja: **o detector recebe uma referência ao objeto**, não uma cópia. Quando você muda as flags dentro do objeto, o detector que já está rodando enxerga a mudança na hora. Isso é bom e você vai aproveitar.

### 2.2 A função que você vai chamar

`backend/analytics/contexto_tempo_real.py`, linha 108:

```python
def construir_contexto_a_partir_de_data(
    data: datetime.date,
    hora: datetime.time,
    obra_viaria_manual: bool = False,
) -> dict:
```

Ela retorna um **dicionário simples**, mais ou menos assim:

```python
{
  "chuva_forte": True,
  "dia_jogo": False,
  "horario_pico": True,
  "feriado": False,
  "obra_viaria": False,
  "timestamp": "2026-09-07T15:00:00",
  "fatores_ativos": ["Chuva Forte / Baixa Visibilidade", "Horário de Pico"],
  "_detalhes": {"precipitacao_mm": 4.2, "confronto": "Palmeiras x Corinthians"}
}
```

As três consultas de rede (Open-Meteo, TheSportsDB, biblioteca `holidays`) já estão protegidas por `try/except` dentro do módulo. Se a internet cair, a função **não levanta exceção** — ela devolve `False` para o fator que falhou e loga um aviso. Você não precisa reimplementar isso; só precisa não quebrar em cima.

---

## 3. ⚠️ O erro que o roteiro do grupo te faria cometer

O `roteiro_execucao_detalhado.md` (Passo 1.3) manda fazer:

```python
st.session_state["contexto_atual"] = contexto   # ← um dict solto
```

**Não faça isso.** No teu código, quem alimenta o `MotorCausaRaiz` e quem vai dentro do `InfracaoDetector` é o **objeto** `st.session_state.contexto`, não uma chave nova de dicionário. Se você criar `contexto_atual` e parar por aí, o dashboard vai mostrar um resumo bonitinho na tela **e o detector vai continuar calculando causa-raiz com todos os fatores em `False`**.

É a pior categoria de bug possível para uma apresentação: nada quebra, nenhum erro aparece, e a causa-raiz sai errada sem ninguém perceber.

**O jeito certo:** guardar o dicionário retornado (para exibir os detalhes na tela) **e** despejar as flags dentro do objeto que já existe:

```python
st.session_state.contexto.atualizar_contexto(
    chuva_forte=dados["chuva_forte"],
    dia_jogo=dados["dia_jogo"],
    horario_pico=dados["horario_pico"],
    feriado=dados["feriado"],
    obra_viaria=obra_viaria,
)
```

Assim tudo que já funciona continua funcionando, e você só troca a **origem** das flags: antes vinham de toggles, agora vêm da API.

### 3.1 Segunda armadilha: o `st.rerun()` em loop

Linha 524-527:

```python
if is_running:
    st.progress(prog, text=status_msg)
    time.sleep(0.04)
    st.rerun()
```

Enquanto um vídeo está sendo processado, **o script inteiro re-executa cerca de 25 vezes por segundo** — a sidebar junto. Se você colocar a chamada de rede solta no corpo do script (do jeito que os toggles estão hoje), você vai disparar dezenas de requisições HTTP por segundo para o Open-Meteo. O app trava, e provavelmente você toma bloqueio da API no meio da demonstração.

Por isso a consulta **tem que ficar atrás de um botão**, com o resultado guardado em `st.session_state`. O código da Seção 5 já faz isso.

---

## 4. Passo a passo

### Passo 0 — Sincronizar e conferir o ponto de partida (10 min)

```powershell
cd "C:\Users\manue\OneDrive - Fundação Escola de Comércio Álvares Penteado\Área de Trabalho\COGNIMOVE"
git status
git pull origin main
pip install -r requirements.txt
python -m pytest backend\tests\ -v
```

- `git status` limpo antes do pull. Se tiver alteração local pendente, resolva agora.
- `holidays` está no `requirements.txt` (última linha), mas confirme que instalou: `python -c "import holidays; print(holidays.__version__)"`.
- Anote o número de testes que passou. É o teu piso — no fim do dia tem que ser esse número ou mais.

**Crie uma branch sua.** Três pessoas empurrando direto na `main` no mesmo dia é pedir conflito:

```powershell
git checkout -b pessoa1-contexto-real
```

---

### Passo 1 — Verificação de fumaça da função (10 min)

Antes de mexer no dashboard, confirme no terminal que a função funciona na tua máquina, com a tua internet:

```powershell
python -c "import datetime; from backend.analytics.contexto_tempo_real import construir_contexto_a_partir_de_data as f; print(f(datetime.date(2026,12,25), datetime.time(18,0)))"
```

Você deve ver um dicionário com `'feriado': True` e `'horario_pico': True` (25/12/2026 cai numa **sexta-feira**, e 18:00 está dentro da janela de pico da tarde).

Se isso não funcionar, o problema é de ambiente/import — resolva aqui, no terminal, onde o erro é legível, e não dentro do Streamlit.

---

### Passo 2 — Adicionar a função de resumo em `frontend/utils_dashboard.py` (15 min)

Por que num arquivo separado: código dentro do `dashboard_streamlit.py` não é testável (o Streamlit executa o script inteiro na importação). O `utils_dashboard.py` já existe justamente para isso e já tem testes em `backend/tests/test_dashboard_utils.py`. Colocando a lógica de resumo lá, você consegue **adicionar testes automatizados ao teu commit** — o que faz a tua entrega passar de "mexi na interface" para "mexi na interface e cobri com teste".

Adicione ao fim de `frontend/utils_dashboard.py`:

```python
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
```

---

### Passo 3 — Escrever os testes dessa função (15 min)

Adicione ao fim de `backend/tests/test_dashboard_utils.py` (o arquivo já importa com `from frontend.utils_dashboard import ...`, siga o mesmo padrão):

```python
from frontend.utils_dashboard import resumir_contexto


def test_resumir_contexto_sem_consulta():
    """Contexto None (usuário ainda não clicou em consultar) não quebra."""
    assert resumir_contexto(None) == "Contexto ainda não consultado."


def test_resumir_contexto_nenhum_fator_ativo():
    """Todos os fatores falsos produz a frase de condição normal."""
    ctx = {"chuva_forte": False, "dia_jogo": False, "horario_pico": False,
           "feriado": False, "obra_viaria": False, "_detalhes": {}}
    assert resumir_contexto(ctx) == "Nenhum fator de risco identificado."


def test_resumir_contexto_multiplos_fatores():
    """Fatores ativos aparecem na frase, com os detalhes numéricos."""
    ctx = {"chuva_forte": True, "dia_jogo": True, "horario_pico": True,
           "feriado": False, "obra_viaria": False,
           "_detalhes": {"precipitacao_mm": 4.24, "confronto": "Palmeiras x Santos"}}
    resumo = resumir_contexto(ctx)
    assert "4.2 mm/h" in resumo
    assert "Palmeiras x Santos" in resumo
    assert "Horário de pico" in resumo
    assert "Feriado" not in resumo


def test_resumir_contexto_detalhes_ausentes_nao_quebra():
    """Se a API falhou e não veio _detalhes, a função ainda responde."""
    ctx = {"chuva_forte": True, "dia_jogo": True}
    resumo = resumir_contexto(ctx)
    assert "0.0 mm/h" in resumo
    assert "Jogo na cidade" in resumo
```

Rode: `python -m pytest backend\tests\test_dashboard_utils.py -v`. Os quatro devem passar.

---

### Passo 4 — Editar o `dashboard_streamlit.py` (45-60 min)

**4a. Import.** Na linha 46-49 já existe o bloco de imports do projeto:

```python
from analytics.contexto_urbano import GerenciadorContextoUrbano
from analytics.causa_raiz import MotorCausaRaiz, Causa
from recomendacoes import RECOMENDACOES_POR_CAUSA
from utils_dashboard import obter_causa_predominante
```

Ajuste para:

```python
from analytics.contexto_urbano import GerenciadorContextoUrbano
from analytics.contexto_tempo_real import construir_contexto_a_partir_de_data
from analytics.causa_raiz import MotorCausaRaiz, Causa
from recomendacoes import RECOMENDACOES_POR_CAUSA
from utils_dashboard import obter_causa_predominante, resumir_contexto
```

`import datetime` **já existe** na linha 21 — não adicione de novo.

> Detalhe técnico, para você não se assustar: o `contexto_tempo_real.py` faz internamente `from backend.analytics.contexto_urbano import ...` (com o prefixo `backend.`), enquanto o dashboard importa `from analytics.contexto_urbano import ...` (sem). Os dois caminhos funcionam porque o `sys.path` do dashboard (linhas 41-44) inclui tanto `backend/` quanto a raiz. Na prática o Python carrega o módulo duas vezes, com duas classes distintas. **Isso não causa problema aqui**, porque a função devolve um dicionário puro — e você só vai usar o dicionário. Só não tente pegar o gerenciador de dentro da função e substituir o `st.session_state.contexto` por ele.

**4b. Substituir o bloco dos toggles.** Apague as **linhas 392 a 419** (do `st.markdown("## 🌧️ Fatores Urbanos (Módulo 3)")` até o fim do bloco `Status do Ambiente`, parando antes do `st.divider()` da linha 421) e cole o código da Seção 5 no lugar.

**4c. Proteger o botão "Iniciar Monitoramento".** Linha 459, hoje:

```python
if iniciar and video_escolhido:
```

Troque por:

```python
if iniciar and video_escolhido:
    if not st.session_state.get("contexto_dados"):
        st.warning("⚠️ Consulte o contexto da gravação (barra lateral) antes de iniciar o monitoramento.")
        st.stop()
```

...e reindente o bloco que vem em seguida (o `with proc_state.lock:` e o resto até o `st.rerun()` da linha 479) para dentro do `if`. **Cuidado com a indentação aqui** — é o ponto mais fácil de errar do dia. Se preferir não mexer na indentação, use a variante alternativa da Seção 5.3.

**4d. Atualizar o docstring.** No topo do arquivo, linha 9, está escrito:

```
Área 2: Simulador de Cenários Urbanos (Fatores externos: Chuva, Jogo, Horário de Pico, Feriado, Obras)
```

Troque para algo como:

```
Área 2: Contexto Urbano Real (fatores obtidos por data/hora via APIs de clima,
        feriados e agenda esportiva; obra viária informada manualmente)
```

Parece detalhe, mas é o tipo de coisa que o professor lê.

---

### Passo 5 — Testes manuais (25 min)

```powershell
streamlit run frontend/dashboard_streamlit.py
```

Rode este roteiro e **anote os resultados numa folha** — eles viram o roteiro da apresentação:

| # | O que fazer | O que tem que acontecer |
|---|---|---|
| 1 | Data `25/12/2026`, hora `18:00` → Consultar | Aparece 🎉 Feriado **e** 🕐 Horário de pico |
| 2 | Data de um sábado qualquer, hora `08:00` → Consultar | **Não** aparece horário de pico (fim de semana nunca é pico) |
| 3 | Uma terça-feira comum, `08:00` → Consultar | Aparece 🕐 Horário de pico, sem feriado |
| 4 | Ligar o toggle 🚧 Obra viária | O resumo atualiza na hora, **sem precisar clicar em Consultar de novo** |
| 5 | Desligar o Wi-Fi e clicar em Consultar | Aparece um aviso discreto, o app **não** mostra tela de erro do Streamlit |
| 6 | Clicar em Iniciar Monitoramento sem ter consultado | Aparece o aviso amarelo, o vídeo não começa |
| 7 | Consultar contexto com 2 fatores → Iniciar → esperar uma infração | O alerta vermelho mostra causa-raiz **diferente** da que aparece sem fator nenhum |

**O teste 7 é o que prova que a tua entrega funcionou.** Se a causa-raiz for idêntica com e sem contexto, você caiu na armadilha da Seção 3 — o objeto não está sendo alimentado.

Jeito rápido de conferir o teste 7: com chuva forte ativa, uma `INVASAO_FAIXA` deve migrar a causa principal para *"Sinalização pouco visível"* (o modificador de chuva soma +0.25 nessa causa, contra 0.35 base de *"Pintura desgastada / ausente"* → 0.50 vs 0.35 depois de normalizar). Com horário de pico, um `BLOQUEIO_CRUZAMENTO` reforça *"Congestionamento"*. Está tudo em `backend/analytics/causa_raiz.py`, linhas 64-70.

---

### Passo 6 — Descobrir datas boas para a demonstração (15 min)

Isto não está no roteiro do grupo, mas vale muito na hora da apresentação. Duas limitações reais das APIs que você precisa conhecer **antes** e não durante:

- **Open-Meteo (chuva):** o endpoint de arquivo histórico tem uns 5 dias de atraso. Se você escolher "ontem", provavelmente vem sem dado e o sistema assume "sem chuva" (silenciosamente, por design). O endpoint de previsão só cobre ~16 dias à frente. Ou seja: **para demonstrar chuva, use uma data de pelo menos uma semana atrás.**
- **TheSportsDB (jogo):** o módulo usa a chave gratuita de teste (`"3"`), que é limitada e nem sempre devolve os jogos brasileiros. Não conte com esse fator na demonstração — se aparecer, é bônus.

Rode este script na raiz do projeto para achar datas em que realmente choveu forte em São Paulo:

```python
# salve como scratch_datas_chuva.py, rode com: python scratch_datas_chuva.py
import datetime, requests

r = requests.get("https://archive-api.open-meteo.com/v1/archive", params={
    "latitude": -23.55, "longitude": -46.63,
    "start_date": "2026-05-01", "end_date": "2026-08-31",
    "hourly": "precipitation", "timezone": "America/Sao_Paulo",
}, timeout=20)
d = r.json()["hourly"]
pares = [(t, v) for t, v in zip(d["time"], d["precipitation"]) if v and v >= 2.5]
pares.sort(key=lambda x: -x[1])
for t, v in pares[:15]:
    dt = datetime.datetime.fromisoformat(t)
    print(f"{dt:%d/%m/%Y %H:%M}  {dt:%A}  {v} mm/h")
```

Escolha da lista uma data que seja **dia de semana entre 17h e 19h** — assim você demonstra chuva **e** horário de pico ao mesmo tempo, dois fatores empilhados, que é o caso mais convincente. Anote essa data. Não apague o script, mas também **não commite ele** (ou coloque em `scratch_frames/`, que já está fora do fluxo principal).

---

### Passo 7 — Testes automatizados e commit (15 min)

```powershell
python -m pytest backend\tests\ -v
```

Tem que dar o número do Passo 0 **+ 4** (os testes novos do `resumir_contexto`).

```powershell
git add frontend/dashboard_streamlit.py frontend/utils_dashboard.py backend/tests/test_dashboard_utils.py
git status
git commit -m "feat(dashboard): substitui toggles manuais por contexto urbano real via data/hora"
git push origin pessoa1-contexto-real
```

**Avise no grupo assim que empurrar** — a Pessoa 3 depende disso para integrar a seleção de vídeo. Mande junto: o nome da branch, e as datas que você validou no Passo 6.

---

## 5. Código pronto para colar

### 5.1 Substitui as linhas 392-419 de `frontend/dashboard_streamlit.py`

```python
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
```

### 5.2 Como fica o restante (não mexa, é só para conferir)

Logo abaixo do bloco acima continua o que já existe hoje nas linhas 421-422:

```python
    st.divider()
    usar_ia = st.checkbox("⚡ Processar com Modelo de IA (YOLOv8 + ByteTrack)", value=True)
```

E as variáveis `chk_chuva`, `chk_jogo`, `chk_pico`, `chk_feriado`, `chk_obra` deixam de existir. Confirme com `Ctrl+F` que nenhuma delas é usada em outro ponto do arquivo (não deveria ser — só apareciam no bloco que você apagou).

### 5.3 Variante do Passo 4c, se você não quiser reindentar

Em vez de aninhar o `if`, deixe o guarda logo acima da linha 459:

```python
    if iniciar and not st.session_state.get("contexto_dados"):
        st.warning("⚠️ Consulte o contexto da gravação (barra lateral) antes de iniciar o monitoramento.")
        iniciar = False

    # Ação de iniciar: dispara worker em thread dedicada (se não houver outra ativa)
    if iniciar and video_escolhido:
        ...
```

Funciona igual e não mexe em nenhuma linha existente além de acrescentar três.

---

## 6. Definição de pronto

- [ ] Escolher data/hora e clicar em Consultar reflete corretamente os 4 fatores automáticos
- [ ] Nenhum toggle manual restante além de obra viária
- [ ] Toggle de obra viária atualiza o resumo sem exigir nova consulta
- [ ] Sem internet, o app avisa e continua funcionando (não mostra traceback do Streamlit)
- [ ] Iniciar monitoramento sem contexto mostra aviso, não quebra
- [ ] **A causa-raiz muda quando o contexto muda** (teste 7 da tabela do Passo 5)
- [ ] `pytest backend/tests/ -v` passando, com 4 testes a mais que no início do dia
- [ ] Branch empurrada e grupo avisado, com as datas de demonstração anotadas

---

## 7. Se der errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `ModuleNotFoundError: analytics.contexto_tempo_real` | Import escrito com prefixo errado | Use exatamente `from analytics.contexto_tempo_real import ...`, igual às linhas vizinhas |
| `ModuleNotFoundError: backend` ao rodar a função | Está rodando de dentro de outra pasta | Rode sempre da raiz do projeto (`COGNIMOVE/`) |
| `ModuleNotFoundError: holidays` | Dependência nova não instalada | `pip install holidays` |
| O dashboard trava ao processar vídeo | Chamada de rede solta no corpo do script | Confirme que a consulta está **dentro** do `if st.button(...)` |
| Causa-raiz não muda com o contexto | Caiu na armadilha da Seção 3 | Confirme que `st.session_state.contexto.atualizar_contexto(...)` está sendo chamado |
| Escolhi data de chuva e veio "sem chuva" | Data recente demais (atraso do arquivo histórico) | Use data de pelo menos 7 dias atrás, conforme Passo 6 |
| `IndentationError` depois do Passo 4c | Reindentação do bloco do `iniciar` | Use a variante da Seção 5.3 |

---

## 8. Ordem sugerida do teu dia

```
09:00  Passo 0 — sincronizar, branch, pytest de partida
09:15  Passo 1 — verificação de fumaça no terminal
09:25  Passos 2 e 3 — resumir_contexto + testes (a parte fácil, feita cedo)
10:00  Passo 4 — editar o dashboard (a parte que exige atenção)
11:00  Passo 5 — testes manuais, anotando resultados
11:30  Passo 6 — caçar as datas boas para a demonstração
11:45  Passo 7 — pytest, commit, push, avisar o grupo
```

Se atrasar, o que pode ser cortado sem prejuízo para a entrega é o Passo 6 (datas de demonstração) e o Passo 4d (docstring). O que **não** pode ser cortado é o teste 7 do Passo 5 — é ele que prova que a integração ficou de pé.
