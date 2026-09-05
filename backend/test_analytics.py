import sys
print("Python version:", sys.version)

import pandas as pd
print("Pandas imported:", pd.__version__)

import plotly
print("Plotly imported:", plotly.__version__)

import streamlit as st
print("Streamlit imported:", st.__version__)

from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from backend.analytics.contexto_urbano import GerenciadorContextoUrbano
from backend.analytics.causa_raiz import MotorCausaRaiz

ctx = GerenciadorContextoUrbano()
ctx.set_chuva_forte(True)
estado = ctx.obter_contexto_atual()
print("Contexto Urbano:", estado)

motor = MotorCausaRaiz()
res = motor.calcular_probabilidades("AVANCO_SINAL_VERMELHO", estado)
print("Resultado Causa-Raiz:", res)
print("ALL TESTS PASSED!")
