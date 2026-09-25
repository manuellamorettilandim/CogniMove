"""
CogniMove — Script de Desenvolvimento / Depuração Manual: testar_regras.py

AVISO: Este script é uma ferramenta legada de prototipagem rápida da lógica de regras (sem ultralytics).
NÃO faz parte da suíte oficial de testes nem do pipeline de produção. Para testes automatizados
oficiais do projeto, execute 'pytest backend/tests/'. Veja backend/detection/NOTAS_SCRIPTS_DEV.md.
"""
import sys, os, types
sys.path.insert(0, os.path.dirname(__file__))

# ── Mock ultralytics para não precisar do pacote ──────────────────────────────
_ul = types.ModuleType("ultralytics")
class _MockYOLO:
    def __init__(self, *a, **k): self.names = {}
    def track(self, *a, **k):    return []
    def predict(self, *a, **k):  return []
_ul.YOLO = _MockYOLO
sys.modules["ultralytics"] = _ul

# ── Imports reais ─────────────────────────────────────────────────────────────
from infracoes.rastreador             import VehicleTrack
from infracoes.regras.faixa_pedestre  import RegraFaixaPedestre, segments_intersect, point_in_polygon
from infracoes.regras.sinal_vermelho  import RegraSinalVermelho, classify_traffic_light_hsv
from infracoes.regras.bloqueio_cruzamento import RegraBloqueioCruzamento
from infracoes.evidencias             import GerenciadorEvidencias
from infracoes.relatorio              import GerenciadorRelatorio
import tempfile, numpy as np, cv2

print("[OK] Todos os módulos importados com sucesso!\n")

PASS = 0; FAIL = 0

def check(cond, msg):
    global PASS, FAIL
    if cond: print(f"  [OK] {msg}"); PASS += 1
    else:    print(f"  [X]  {msg}  <- FALHOU"); FAIL += 1

# ── Teste 1: VehicleTrack ────────────────────────────────────────────────────
print("=== Teste 1: VehicleTrack ===")
t = VehicleTrack(1, 2, "Carro")
t.update(1, (100, 150, 200, 250), 0.85)
t.update(2, (105, 160, 205, 260), 0.87)

exp_bottom = ((105+205)//2, 260)
exp_cent   = ((105+205)//2, (160+260)//2)
check(t.current["frame"]     == 2,          "frame atual = 2")
check(t.previous["frame"]    == 1,          "frame anterior = 1")
check(t.current["bottom_pt"] == exp_bottom, f"bottom_pt = {exp_bottom}")
check(t.current["centroid"]  == exp_cent,   f"centroid = {exp_cent}")

# ── Teste 2: Geometria ───────────────────────────────────────────────────────
print("\n=== Teste 2: segments_intersect ===")
check(segments_intersect((0,0),(10,10),(0,10),(10,0)) == True,  "cruzamento em X")
check(segments_intersect((0,0),(5,5), (10,0),(20,0))  == False, "paralelos, sem cruzamento")

print("\n=== Teste 3: point_in_polygon ===")
box = [[0,0],[100,0],[100,100],[0,100]]
check(point_in_polygon((50,50),  box), "ponto dentro do retângulo")
check(not point_in_polygon((150,50), box), "ponto fora do retângulo")

# ── Teste 4: RegraFaixaPedestre ──────────────────────────────────────────────
print("\n=== Teste 4: RegraFaixaPedestre — cruzamento de linha ===")
linha = {"name": "Linha Teste", "pt1": [0, 200], "pt2": [640, 200], "color": [0,255,255]}
regra_fp = RegraFaixaPedestre(lines=[linha], cooldown_frames=10)

# Track: ponto de base sobe de y=190 para y=220 → cruza a linha y=200
tk1 = VehicleTrack(10, 2, "Carro")
tk1.update(1, (300, 140, 400, 190), 0.9)  # bottom_pt=(350, 190) — acima
tk1.update(2, (300, 170, 400, 220), 0.9)  # bottom_pt=(350, 220) — abaixo

inf = regra_fp.checar(None, [tk1], "unknown", 2)
check(len(inf) == 1,                          "1 infração detectada")
check(inf[0]["tipo"] == "INVASAO_FAIXA",     "tipo correto")
check(inf[0]["track_id"] == 10,              "track_id correto")

# Cooldown: segunda checagem no frame seguinte não deve alertar
inf2 = regra_fp.checar(None, [tk1], "unknown", 3)
check(len(inf2) == 0, "cooldown bloqueou re-alerta")

# ── Teste 5: RegraFaixaPedestre — invasão de polígono ───────────────────────
print("\n=== Teste 5: RegraFaixaPedestre — invasão de polígono ===")
poly_zone = {"name": "Bike Box", "points": [[100,100],[300,100],[300,300],[100,300]]}
regra_poly = RegraFaixaPedestre(lines=[], polygons=[poly_zone], cooldown_frames=5)

tk2 = VehicleTrack(20, 1, "Bicicleta")
tk2.update(1, (150, 150, 250, 290), 0.8)  # bottom_pt=(200,290) → dentro do polígono

inf3 = regra_poly.checar(None, [tk2], "unknown", 1)
check(len(inf3) == 1,                     "invasão de polígono detectada")
check(inf3[0]["tipo"] == "INVASAO_FAIXA", "tipo correto")

# ── Teste 6: RegraBloqueioCruzamento ────────────────────────────────────────
print("\n=== Teste 6: RegraBloqueioCruzamento ===")
zona = {"name": "Cruzamento", "points": [[100,100],[300,100],[300,300],[100,300]]}
regra_bq = RegraBloqueioCruzamento([zona], fps=10.0, threshold_seconds=2.0)

tk3 = VehicleTrack(30, 2, "Carro")

# Frames 1-19: dentro da zona
for f in range(1, 20):
    tk3.update(f, (150, 150, 250, 250), 0.8)

# Chamar checar no frame 1 para registrar entrada na zona
regra_bq.checar(None, [tk3], "unknown", 1)

# Frame 19 (1.9s com fps=10) — abaixo do threshold de 20 frames
inf4 = regra_bq.checar(None, [tk3], "unknown", 19)
check(len(inf4) == 0, "abaixo do threshold (1.9s) -> sem infração")

# Frame 21 (2.0s+ com fps=10 → 20 frames) — acima do threshold
tk3.update(21, (150, 150, 250, 250), 0.8)
inf5 = regra_bq.checar(None, [tk3], "unknown", 21)
check(len(inf5) == 1,                           "acima do threshold (2.1s) -> infração")
check(inf5[0]["tipo"] == "BLOQUEIO_CRUZAMENTO", "tipo correto")
check(inf5[0]["segundos_bloqueio"] >= 2.0,      "tempo de bloqueio correto")

# ── Teste 7: GerenciadorRelatorio ───────────────────────────────────────────
print("\n=== Teste 7: GerenciadorRelatorio ===")
with tempfile.TemporaryDirectory() as tmpdir:
    rel = GerenciadorRelatorio(tmpdir, camera_name="CamTest")
    rel.adicionar({
        "tipo": "INVASAO_FAIXA", "descricao": "Cruzou linha",
        "track_id": 1, "classe": "Carro", "confianca": 0.9,
        "frame": 42,   "timestamp": "2026-01-01T12:00:00"
    }, {"screenshot": "foto.jpg"})
    recs  = rel.get_records()
    stats = rel.get_stats()
check(len(recs) == 1,                     "1 registro no relatório")
check(recs[0]["camera"] == "CamTest",     "camera correta")
check(recs[0]["screenshot"] == "foto.jpg","screenshot salvo")
check(stats["total"] == 1,               "stats.total = 1")
check(stats["INVASAO_FAIXA"] == 1,       "stats por tipo correto")

# ── Teste 8: classify_traffic_light_hsv ─────────────────────────────────────
print("\n=== Teste 8: classify_traffic_light_hsv ===")

# Vermelho puro em BGR = (0, 0, 255)
img_r = np.zeros((90, 30, 3), dtype=np.uint8)
img_r[0:30, :] = (0, 0, 255)    # topo → vermelho
state_r = classify_traffic_light_hsv(img_r, (0, 0, 30, 90))
check(state_r == "red", f"vermelho detectado (got '{state_r}')")

# Verde puro em BGR = (0, 255, 0)
img_g = np.zeros((90, 30, 3), dtype=np.uint8)
img_g[60:90, :] = (0, 255, 0)   # base → verde
state_g = classify_traffic_light_hsv(img_g, (0, 0, 30, 90))
check(state_g == "green", f"verde detectado (got '{state_g}')")

# ── Resultado ────────────────────────────────────────────────────────────────
print("\n" + "="*52)
if FAIL == 0:
    print(f"[PASS] TODOS OS {PASS} TESTES PASSARAM!")
else:
    print(f"[WARN] {PASS} OK | {FAIL} FALHOU(ARAM)")
print("="*52)
sys.exit(0 if FAIL == 0 else 1)
