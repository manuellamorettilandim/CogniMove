# Prompt 8 — Aviso de fonte externa indisponível

Cole no Claude Code, na raiz do projeto. Termina em **66 testes** (62 + 4 novos).

```
Falta implementar um requisito da minha tarefa: quando uma fonte externa (clima ou
jogos) falha, o dashboard deve mostrar um aviso discreto dizendo qual fator não pôde
ser confirmado, em vez de silenciosamente assumir False.

Hoje isso não aparece porque construir_contexto_a_partir_de_data() trata as falhas
internamente com try/except e só emite logger.warning(...) — nada chega na interface.

RESTRIÇÃO IMPORTANTE: não altere backend/analytics/contexto_tempo_real.py. As
assinaturas daquelas funções estão cobertas por testes; mudá-las quebraria a suíte.
A solução é capturar os warnings que o módulo já emite.

ARQUIVO 1 — frontend/utils_dashboard.py
Acrescente ao final, mantendo tudo que já existe. Os imports vão no topo do arquivo,
junto com o `import pandas as pd`:

import logging
from contextlib import contextmanager


class _ColetorDeAvisos(logging.Handler):
    """Handler que apenas acumula as mensagens de aviso emitidas por um logger."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.mensagens: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.mensagens.append(record.getMessage())


@contextmanager
def coletar_avisos(nome_logger: str):
    """Captura os warnings emitidos por um logger durante o bloco `with`.

    Uso:
        with coletar_avisos(minha_funcao.__module__) as avisos:
            minha_funcao()
        # `avisos` agora é a lista de mensagens capturadas
    """
    logger = logging.getLogger(nome_logger)
    coletor = _ColetorDeAvisos()
    nivel_anterior = logger.level
    logger.setLevel(logging.WARNING)
    logger.addHandler(coletor)
    try:
        yield coletor.mensagens
    finally:
        logger.removeHandler(coletor)
        logger.setLevel(nivel_anterior)


def traduzir_avisos_contexto(mensagens: list[str]) -> list[str]:
    """Converte os avisos técnicos das fontes externas em texto para o usuário.

    Remove duplicatas preservando a ordem de ocorrência.
    """
    amigaveis: list[str] = []
    for m in mensagens:
        texto = m.lower()
        if "clima" in texto or "open-meteo" in texto:
            amigaveis.append("Não foi possível confirmar o clima — assumindo sem chuva.")
        elif "jogo" in texto or "sportsdb" in texto:
            amigaveis.append("Não foi possível confirmar jogos na cidade — assumindo sem jogo.")
        else:
            amigaveis.append(f"Fonte externa indisponível: {m}")

    vistos: set[str] = set()
    unicos: list[str] = []
    for a in amigaveis:
        if a not in vistos:
            vistos.add(a)
            unicos.append(a)
    return unicos

ARQUIVO 2 — backend/tests/test_dashboard_utils.py
Adicione ao final 4 testes, no estilo dos que já existem:
  a) traduzir_avisos_contexto com uma mensagem contendo "Open-Meteo" devolve o texto
     de chuva
  b) mensagem contendo "TheSportsDB" devolve o texto de jogo
  c) duas mensagens iguais viram uma só (deduplicação), e uma mensagem que não bate
     com nenhum padrão é repassada com o prefixo "Fonte externa indisponível:"
  d) coletar_avisos captura um logger.warning emitido dentro do bloco E remove o
     handler ao sair (verifique que um warning emitido DEPOIS do bloco não é capturado)

ARQUIVO 3 — frontend/dashboard_streamlit.py
1. Na linha de import do utils_dashboard, traga também `coletar_avisos` e
   `traduzir_avisos_contexto`.
2. Dentro do `if st.button("🔍 Consultar contexto real", ...)`, envolva a chamada:

            try:
                with coletar_avisos(construir_contexto_a_partir_de_data.__module__) as avisos:
                    st.session_state.contexto_dados = construir_contexto_a_partir_de_data(
                        data_gravacao, hora_gravacao, obra_viaria_manual=obra_viaria
                    )
                st.session_state.contexto_avisos = traduzir_avisos_contexto(avisos)
                st.session_state.contexto_erro = None
            except Exception as e:
                st.session_state.contexto_dados = None
                st.session_state.contexto_avisos = []
                st.session_state.contexto_erro = str(e)

   Uso `__module__` de propósito: o módulo é carregado com nomes diferentes no
   dashboard e nos testes, e assim o nome do logger sempre bate.
3. Logo depois do bloco que exibe `contexto_erro`, adicione:

    for aviso in st.session_state.get("contexto_avisos", []):
        st.warning(aviso)

VERIFICAÇÃO
py_compile no dashboard, e `python -m pytest backend/tests/ -q` — tem que dar 66
(eram 62 + 4 novos). Me mostre o git diff. Não commite.
```

## Como testar depois

Desligue o Wi-Fi e clique em **Consultar contexto real**. Devem aparecer dois avisos amarelos (clima e jogos) e o feriado continuar funcionando — porque feriado vem da biblioteca local `holidays`, sem rede. Esse contraste é bom de mostrar na apresentação.
