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

## Regras do Frontend (Pessoa 3 — Raíssa)

Stack real: Flask (frontend/app.py) servindo um único frontend/templates/index.html
(SPA por hash, seções .cm-section trocadas via NavModule) + frontend/static/css/style.css
(design system via CSS custom properties em :root) + frontend/static/js/site.js (módulos
IIFE: ThemeModule, NavModule, MonitorModule, AnaliseModule, RelatorioModule,
InteratividadeModule). NÃO É REACT. Não crie arquivos .jsx, não introduza um bundler,
não proponha migração de framework — não há tempo antes da feira.

Identidade visual: tema escuro por padrão com toggle para claro (data-theme="dark"|"light"
na tag <html>), paleta base em roxo/violeta. Mudanças de cor/token vão em :root e
[data-theme="light"] no topo do style.css — tudo no resto do arquivo usa var(--x), então
mudar o token no topo já propaga.

Dado real vs mock: as páginas Análise, Relatórios e Interatividade dependem de arquivos
.json em backend/outputs/curados/real/ e backend/outputs/curados/gta/, servidos por
/api/curados e /api/curados/gta (rotas já existem em app.py). Essas pastas podem não
existir ainda — se não existirem, é ESPERADO que a tela mostre o estado vazio, isso não
é bug do frontend. Nunca invente um schema de JSON novo sem eu confirmar — o formato
atual está documentado no PLANO_PESSOA_3_FRONTEND.md, seção 3.

Não rode `python frontend/app.py` deixando o processo aberto sem eu pedir (ele não
termina sozinho). Não faça git commit/push sem eu pedir explicitamente. Não reformate
nem "limpe" código fora do escopo pedido.

