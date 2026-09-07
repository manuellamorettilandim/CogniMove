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
