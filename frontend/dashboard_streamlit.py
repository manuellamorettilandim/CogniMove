"""
CogniMove — Estação Interativa (Módulo 4)

Plataforma inteligente para detecção automática de infrações de trânsito
com análise de causa-raiz e integração de dados urbanos em tempo real.

Estrutura visual em 3 áreas (Seção 4.5 do artigo):
  Área 1: Simulador de Câmera (Vídeo analisado pela IA com caixas delimitadoras e alertas explicativos)
  Área 2: Simulador de Cenários Urbanos (Fatores externos: Chuva, Jogo, Horário de Pico, Feriado, Obras)
  Área 3: Centro de Diagnóstico Inteligente (Gráficos, causas-raiz, correlações e recomendações públicas)

Uso:
  streamlit run frontend/dashboard_streamlit.py
"""
from __future__ import annotations

import os
import sys
import json
import time
import datetime
import re
import threading
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Paths absolutos ───────────────────────────────────────────────────────────
_FRONTEND = Path(__file__).resolve().parent       # frontend/
_ROOT     = _FRONTEND.parent                      # COGNIMOVE/
_BACKEND  = _ROOT / "backend"
_OUTPUTS  = _BACKEND / "outputs"
_REPORTS  = _OUTPUTS / "relatorios"
_PRESETS  = _BACKEND / "calibration" / "presets"

sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "detection"))

from analytics.contexto_urbano import GerenciadorContextoUrbano
from analytics.causa_raiz import MotorCausaRaiz


# ── Configuração da Página ────────────────────────────────────────────────────

st.set_page_config(
    page_title="CogniMove — Estação Interativa de Mobilidade",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design System & Estilos Modernos ──────────────────────────────────────────

st.markdown("""
<style>
    /* Estilo geral */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Header principal */
    .main-header {
        background: linear-gradient(135deg, #10162f 0%, #1a234e 50%, #0c3358 100%);
        border: 1px solid rgba(0, 229, 255, 0.25);
        border-radius: 14px;
        padding: 1.4rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    .main-header h1 {
        color: #00e5ff;
        font-size: 2.1rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin: 0;
    }
    .main-header p {
        color: #90a4ae;
        font-size: 0.98rem;
        margin-top: 0.35rem;
        margin-bottom: 0;
    }
    .badge-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        background: rgba(0, 229, 255, 0.15);
        color: #00e5ff;
        border: 1px solid rgba(0, 229, 255, 0.35);
        margin-top: 8px;
    }

    /* Cards de métrica */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #161b22, #0d1117);
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stMetric"] label {
        color: #58a6ff !important;
        font-weight: 600;
        font-size: 0.85rem;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #f0f6fc !important;
        font-weight: 700;
    }

    /* Alertas de infração */
    .infraction-alert {
        background: rgba(248, 81, 73, 0.15);
        border-left: 4px solid #f85149;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 12px;
        color: #ff7b72;
        font-size: 0.92rem;
    }

    /* Painel de Recomendações */
    .policy-box {
        background: linear-gradient(145deg, #0e2a27, #13232f);
        border: 1px solid #238636;
        border-radius: 10px;
        padding: 14px 18px;
        margin-top: 10px;
        color: #7ee787;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Inicialização do Estado Compartilhado ─────────────────────────────────────

class VideoProcessingState:
    """Estrutura protegida por lock para comunicação thread-safe com o Streamlit."""
    def __init__(self):
        self.lock = threading.Lock()
        self.is_running = False
        self.stop_requested = False
        self.latest_frame = None
        self.latest_infractions = []
        self.progress = 0.0
        self.frame_idx = 0
        self.total_frames = 0
        self.status_message = "Pronto para iniciar."
        self.error_message = None
        self.completed = False
        self.thread = None


def processar_video_worker(state: VideoProcessingState, video_path: str, preset_name: str, usar_ia: bool, contexto, motor):
    """Executa a leitura e detecção de frames em segundo plano em thread separada."""
    with state.lock:
        state.is_running = True
        state.stop_requested = False
        state.completed = False
        state.error_message = None
        state.status_message = "Iniciando processamento..."
        state.progress = 0.0
        state.frame_idx = 0

    detector = None
    if usar_ia:
        try:
            from infracoes.detector import InfracaoDetector
            detector = InfracaoDetector(
                source          = video_path,
                preset_name     = preset_name,
                camera_name     = preset_name.replace("_", " ").title(),
                show_window     = False,
                contexto_urbano = contexto,
                motor_causa_raiz= motor,
            )
        except Exception as e:
            with state.lock:
                state.error_message = f"Erro ao instanciar detector com IA: {e}"
                state.is_running = False
                state.status_message = "Erro na inicialização"
            return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        with state.lock:
            state.error_message = f"Não foi possível ler o arquivo: {video_path}"
            state.is_running = False
            state.status_message = "Erro ao abrir vídeo"
        return

    try:
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        with state.lock:
            state.total_frames = total_frames

        if detector:
            detector._setup(w, h, fps)

        frame_idx = 0
        while cap.isOpened():
            with state.lock:
                if state.stop_requested:
                    break

            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            infractions = []
            if detector:
                annotated_frame, infractions = detector._process_frame(frame)
                display_frame = annotated_frame
            else:
                display_frame = frame

            # Redimensionar para exibição se necessário
            rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            max_w = 700
            if w > max_w:
                scale = max_w / w
                rgb = cv2.resize(rgb, (max_w, int(h * scale)))

            prog = min(frame_idx / total_frames, 1.0) if total_frames > 0 else 0.0

            with state.lock:
                state.latest_frame = rgb
                state.latest_infractions = infractions
                state.progress = prog
                state.frame_idx = frame_idx
                state.status_message = f"Processando frame {frame_idx}/{total_frames}" if total_frames > 0 else f"Frame {frame_idx}"

            time.sleep(0.03)

    except Exception as e:
        with state.lock:
            state.error_message = f"Erro durante processamento: {e}"
    finally:
        cap.release()
        if detector and hasattr(detector, "stop"):
            try:
                detector.stop()
            except Exception:
                pass
        with state.lock:
            state.is_running = False
            if state.stop_requested:
                state.status_message = "⏹️ Processamento interrompido pelo usuário."
            else:
                state.completed = True
                state.status_message = "✅ Execução concluída com sucesso!"


if "proc_state" not in st.session_state:
    st.session_state.proc_state = VideoProcessingState()

if "contexto" not in st.session_state:
    st.session_state.contexto = GerenciadorContextoUrbano()

if "motor" not in st.session_state:
    st.session_state.motor = MotorCausaRaiz()

if "processando" not in st.session_state:
    st.session_state.processando = False


# ── Utilitários de Dados ──────────────────────────────────────────────────────

def encontrar_csv_mais_recente() -> str | None:
    """Retorna o CSV de relatório mais recente."""
    if not _REPORTS.exists():
        return None
    csvs = sorted(_REPORTS.glob("*.csv"), key=os.path.getmtime, reverse=True)
    return str(csvs[0]) if csvs else None


def carregar_dados() -> pd.DataFrame:
    """Lê o CSV mais recente e garante tipagem."""
    csv_path = encontrar_csv_mais_recente()
    if csv_path and os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, encoding="utf-8")
            if not df.empty:
                return df
        except Exception:
            pass
    return pd.DataFrame()


def listar_videos() -> list[str]:
    """Lista todos os vídeos disponíveis nas pastas de vídeo."""
    candidatos = []
    pastas = [_ROOT / "videos_teste", _ROOT / "videos_originais", _ROOT]
    for p in pastas:
        if p.exists():
            for ext in ("*.mp4", "*.avi", "*.mov", "*.mkv"):
                candidatos.extend(p.glob(ext))
    return sorted(list(set(str(v) for v in candidatos)))


def listar_presets() -> list[str]:
    """Lista presets de calibração disponíveis."""
    if _PRESETS.exists():
        return [p.stem for p in _PRESETS.glob("*.json")]
    return ["general"]


# ══════════════════════════════════════════════════════════════════════════════
#  CABEÇALHO
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1>🚦 CogniMove — Estação Interativa de Mobilidade Urbana</h1>
    <p>Detecção Visual de Infrações com IA • Análise Probabilística de Causa-Raiz • Integração de Fatores Urbanos em Tempo Real</p>
    <div class="badge-pill">Módulos 1, 2, 3 e 4 Conectados • Abordagem Diagnóstica e Preventiva</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  ÁREA 2: SIMULADOR DE FATORES EXTERNOS E CONTROLES (BARRA LATERAL)
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 📍 Seleção de Local e Vídeo")

    presets = listar_presets()
    preset_escolhido = st.selectbox(
        "Cruzamento Monitorado:",
        options=presets,
        format_func=lambda x: f"Cruzamento: {x.replace('_', ' ').title()}",
        index=0 if presets else None,
    )

    videos = listar_videos()
    if videos:
        video_escolhido = st.selectbox(
            "Fluxo de Vídeo (Câmera Urbana):",
            options=videos,
            format_func=lambda x: Path(x).name,
            index=0,
        )
    else:
        video_escolhido = None
        st.warning("Nenhum arquivo de vídeo encontrado.")

    arquivo_enviado = st.file_uploader(
        "Ou envie um vídeo próprio:",
        type=["mp4", "avi", "mov", "mkv"],
        help="Envie um vídeo do seu computador para processar com o CogniMove.",
    )

    # Manutenção futura: implementar limpeza automática de uploads antigos em backend/outputs/uploads/ para evitar acúmulo em disco
    UPLOADS_DIR = _OUTPUTS / "uploads"
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    if arquivo_enviado is not None:
        nome_seguro = re.sub(r'[^A-Za-z0-9_.-]', '_', arquivo_enviado.name)
        caminho_upload = UPLOADS_DIR / nome_seguro
        with open(caminho_upload, "wb") as f:
            f.write(arquivo_enviado.getbuffer())
        video_escolhido = str(caminho_upload)
        st.success(f"Vídeo '{arquivo_enviado.name}' carregado com sucesso.")

    st.divider()

    st.markdown("## 🌧️ Fatores Urbanos (Módulo 3)")
    st.caption("Ative os cenários simulados para recalcular probabilidades em tempo real:")

    chk_chuva   = st.toggle("🌧️ Simular Chuva Forte", key="toggle_chuva")
    chk_jogo    = st.toggle("⚽ Simular Dia de Jogo / Evento", key="toggle_jogo")
    chk_pico    = st.toggle("🕐 Simular Horário de Pico", key="toggle_pico")
    chk_feriado = st.toggle("🎉 Simular Feriado", key="toggle_feriado")
    chk_obra    = st.toggle("🚧 Simular Obra Viária", key="toggle_obra")

    # Atualiza o gerenciador em tempo real
    st.session_state.contexto.atualizar_contexto(
        chuva_forte=chk_chuva,
        dia_jogo=chk_jogo,
        horario_pico=chk_pico,
        feriado=chk_feriado,
        obra_viaria=chk_obra,
    )

    ctx_atual = st.session_state.contexto.obter_contexto_atual()
    ativos = ctx_atual["fatores_ativos"]

    st.markdown("---")
    st.markdown("### 📊 Status do Ambiente:")
    if ativos:
        for f in ativos:
            st.markdown(f"🔹 **{f}**")
    else:
        st.caption("Condições operacionais normais (padrão).")

    st.divider()
    usar_ia = st.checkbox("⚡ Processar com Modelo de IA (YOLOv8 + ByteTrack)", value=True)


# ══════════════════════════════════════════════════════════════════════════════
#  DIVISÃO PRINCIPAL EM DUAS COLUNAS
# ══════════════════════════════════════════════════════════════════════════════

col_camera, col_analise = st.columns([1.6, 1.4])


# ══════════════════════════════════════════════════════════════════════════════
#  ÁREA 1: SIMULADOR DE CÂMERA URBANA (VÍDEO + DETECÇÃO VISUAL)
# ══════════════════════════════════════════════════════════════════════════════

with col_camera:
    st.markdown("### 📹 Área 1: Simulador de Câmera Urbana")
    st.caption(f"Cruzamento selecionado: **{preset_escolhido.replace('_', ' ').title()}**")

    frame_placeholder = st.empty()
    alert_placeholder = st.empty()

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        iniciar = st.button("▶️ Iniciar Monitoramento", type="primary", use_container_width=True)
    with btn_col2:
        parar = st.button("⏹️ Parar", use_container_width=True)

    proc_state = st.session_state.proc_state

    # Ação de parar: seta flag protegida por lock
    if parar:
        with proc_state.lock:
            proc_state.stop_requested = True
        st.session_state.processando = False
        st.rerun()

    # Ação de iniciar: dispara worker em thread dedicada (se não houver outra ativa)
    if iniciar and video_escolhido:
        with proc_state.lock:
            ja_executando = proc_state.is_running

        if not ja_executando:
            t = threading.Thread(
                target=processar_video_worker,
                args=(
                    proc_state,
                    video_escolhido,
                    preset_escolhido,
                    usar_ia,
                    st.session_state.contexto,
                    st.session_state.motor,
                ),
                daemon=True,
            )
            proc_state.thread = t
            t.start()
            st.session_state.processando = True
            st.rerun()

    # Leitura do estado mais recente da thread
    with proc_state.lock:
        is_running = proc_state.is_running
        display_frame = proc_state.latest_frame
        infractions = list(proc_state.latest_infractions)
        prog = proc_state.progress
        status_msg = proc_state.status_message
        err_msg = proc_state.error_message
        completed = proc_state.completed

    st.session_state.processando = is_running

    if err_msg:
        st.error(err_msg)

    if display_frame is not None:
        frame_placeholder.image(display_frame, use_container_width=True)
    elif not video_escolhido:
        frame_placeholder.info("Nenhum arquivo de vídeo carregado. Adicione vídeos na pasta `videos_originais/` ou envie pelo campo acima.")
    else:
        frame_placeholder.caption("Clique em '▶️ Iniciar Monitoramento' para começar.")

    # Se houver infrações detectadas no frame mais recente, exibir alerta estilo Seção 4.5
    if infractions:
        for inf in infractions:
            tipo_legivel = inf["tipo"].replace("_", " ").title()
            conf_pct = int(float(inf.get("confianca", 0.95)) * 100)

            # Diagnóstico instantâneo
            ctx = st.session_state.contexto.obter_contexto_atual()
            causa_calc = st.session_state.motor.calcular_probabilidades(inf["tipo"], ctx)
            causa_top = causa_calc.get("causa_principal", "Em investigação")
            causa_conf = int(float(causa_calc.get("confianca", 0.5)) * 100)

            alert_placeholder.markdown(
                f'<div class="infraction-alert">'
                f'🚨 <b>Infração Detectada:</b> {tipo_legivel} — Confiança da IA: <b>{conf_pct}%</b><br>'
                f'🔍 <b>Causa-Raiz Provável:</b> {causa_top} (Probabilidade: <b>{causa_conf}%</b>)'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Atualização fluida da interface
    if is_running:
        st.progress(prog, text=status_msg)
        time.sleep(0.04)
        st.rerun()
    elif completed:
        st.progress(1.0, text=status_msg)
        alert_placeholder.success("Processamento do fluxo finalizado. Os relatórios foram salvos e integrados.")
    elif status_msg and "interrompido" in status_msg:
        st.warning(status_msg)


# ══════════════════════════════════════════════════════════════════════════════
#  ÁREA 3: CENTRO DE DIAGNÓSTICO INTELIGENTE E CAUSA-RAIZ
# ══════════════════════════════════════════════════════════════════════════════

with col_analise:
    st.markdown("### 🧠 Área 3: Centro de Diagnóstico Inteligente")
    st.caption("Visão diagnóstica orientada à infraestrutura e causas-raiz urbanas.")

    df = carregar_dados()

    if df.empty:
        st.info("Nenhum registro de infração encontrado. Inicie o monitoramento ou consulte relatórios.")
    else:
        # 1. Métricas principais
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("Total de Infrações", len(df))
        with kpi2:
            if "tipo" in df.columns:
                st.metric("Tipos Identificados", df["tipo"].nunique())
        with kpi3:
            if "causa_principal" in df.columns:
                top_causa = df["causa_principal"].mode().iloc[0] if not df["causa_principal"].empty else "N/A"
                st.metric("Causa Predominante", top_causa[:18] + "…" if len(top_causa) > 18 else top_causa)

        st.divider()

        # 2. Gráfico de Pizza: Causa-Raiz (Como ilustrado na Seção 4.5 do artigo)
        if "causa_principal" in df.columns:
            causa_cont = df["causa_principal"].value_counts().reset_index()
            causa_cont.columns = ["Causa-Raiz", "Ocorrências"]

            fig_pizza = px.pie(
                causa_cont,
                names="Causa-Raiz",
                values="Ocorrências",
                title="Distribuição Probabilística de Causas-Raiz",
                hole=0.42,
                color_discrete_sequence=["#00e5ff", "#f50057", "#ffb300", "#00e676", "#7c4dff"],
            )
            fig_pizza.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e0e0e0"),
                title_font_color="#00e5ff",
                height=310,
                margin=dict(t=40, b=10, l=10, r=10),
            )
            st.plotly_chart(fig_pizza, use_container_width=True)

        st.divider()

        # 3. Gráfico de Barras: Infrações por Tipo
        if "tipo" in df.columns:
            tipo_cont = df["tipo"].value_counts().reset_index()
            tipo_cont.columns = ["Tipo", "Total"]
            tipo_cont["Tipo"] = tipo_cont["Tipo"].str.replace("_", " ").str.title()

            fig_bar = px.bar(
                tipo_cont,
                x="Tipo",
                y="Total",
                title="Incidência de Infrações por Categoria",
                color="Tipo",
                color_discrete_sequence=px.colors.qualitative.Prism,
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e0e0e0"),
                title_font_color="#00e5ff",
                showlegend=False,
                height=260,
                margin=dict(t=40, b=10, l=10, r=10),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # 4. Recomendações e Políticas Baseadas em Evidências (Seção 5 do artigo)
        st.markdown("#### 🏛️ Recomendações Urbanas Inteligentes (Apoio à Gestão)")

        # Lógica explicativa baseada nas causas predominantes
        if "causa_principal" in df.columns:
            top_causa = df["causa_principal"].mode().iloc[0] if not df["causa_principal"].empty else ""
            total_inf = len(df)
            causa_count = (df["causa_principal"] == top_causa).sum()
            pct_top = int((causa_count / total_inf) * 100) if total_inf > 0 else 0

            recs = {
                "Pintura desgastada / ausente": "Recomenda-se repintura imediata e aplicação de sinalização retrorrefletiva na faixa de pedestres para garantir visibilidade noturna e em dias chuvosos.",
                "Tempo semafórico inadequado": "Recomenda-se reprogramação dos ciclos semafóricos junto à CET, com aumento do tempo de verde e tempo de amarelo de segurança nos horários de pico.",
                "Congestionamento": "Recomenda-se sincronismo de onda verde e escalonamento de agentes de trânsito para evitar retenção na área de bloqueio de cruzamento.",
                "Ausência de segregador físico": "Recomenda-se instalação de tachões ou defensas físicas segregando a faixa exclusiva/ciclovia para coibir invasões recorrentes.",
                "Baixa visibilidade": "Recomenda-se reforço de iluminação viária LED e semáforos repetidores em pórticos elevados.",
                "Sinalização pouco visível": "Recomenda-se poda de árvores que obstruem placas e repaginação da geometria de aproximação viária.",
            }
            rec_texto = recs.get(top_causa, "Recomenda-se inspeção técnica no local para avaliação dos conflitos entre pedestres e veículos.")

            st.markdown(
                f'<div class="policy-box">'
                f'📌 <b>Diagnóstico Sistêmico:</b> <b>{pct_top}%</b> dos eventos registrados nesta via estão vinculados a: <i>"{top_causa}"</i>.<br>'
                f'🛠️ <b>Intervenção Sugerida:</b> {rec_texto}'
                f'</div>',
                unsafe_allow_html=True,
            )

        # 5. Tabela de Registros com Auditoria Humana (Seção 6 do artigo)
        with st.expander("📋 Auditoria de Ocorrências e Evidências"):
            colunas_exibir = [c for c in ["timestamp", "tipo", "confianca", "causa_principal", "causa_confianca", "cenarios_ativos"] if c in df.columns]
            st.dataframe(df[colunas_exibir], use_container_width=True, height=220)


# ══════════════════════════════════════════════════════════════════════════════
#  RODAPÉ
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.markdown(
    "<div style='text-align: center; color: #484f58; font-size: 0.85rem;'>"
    "CogniMove © 2026 — Pesquisa em Inteligência Artificial e Mobilidade Urbana • FECAP"
    "</div>",
    unsafe_allow_html=True,
)
