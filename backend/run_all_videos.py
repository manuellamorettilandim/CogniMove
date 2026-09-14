#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_HERE))

from backend.detection.infracoes.detector import InfracaoDetector
from backend.analytics.contexto_urbano import GerenciadorContextoUrbano
from backend.analytics.causa_raiz import MotorCausaRaiz

VIDEOS = [
    {
        "id": "video_teste1",
        "grupo": "real",
        "path": str(_ROOT / "videos_originais" / "video_teste_recorte.mp4"),
        "preset": "cruzamento_centro",
        "camera": "cruzamento_centro_cam1",
    },
    {
        "id": "video_teste2",
        "grupo": "real",
        "path": str(_ROOT / "videos_originais" / "video_teste2_recorte.mp4"),
        "preset": "avenida_norte",
        "camera": "avenida_norte_cam2",
    },
    {
        "id": "video_teste3",
        "grupo": "real",
        "path": str(_ROOT / "videos_originais" / "video_teste3_recorte.mp4"),
        "preset": "invasao_faixa",
        "camera": "invasao_faixa_cam3",
    },
    {
        "id": "video_teste4",
        "grupo": "gta",
        "path": str(_ROOT / "videos_originais" / "video_teste5_recorte.mp4"),
        "preset": "gta2",
        "camera": "gta_cam1",
    },

]

def main():
    resultados_globais = {}

    for item in VIDEOS:
        vid_id = item["id"]
        path = item["path"]
        preset = item["preset"]
        camera = item["camera"]
        grupo = item["grupo"]

        print(f"\n============================================================")
        print(f" PROCESSANDO [{grupo.upper()}] {vid_id} ({preset})")
        print(f" File: {path}")
        print(f"============================================================")

        out_dir = str(_HERE / "outputs" / "runs" / vid_id)
        os.makedirs(out_dir, exist_ok=True)

        contexto_urbano = GerenciadorContextoUrbano()
        motor_causa_raiz = MotorCausaRaiz()

        detector = InfracaoDetector(
            source=path,
            preset_name=preset,
            models_dir=str(_HERE / "models"),
            output_dir=out_dir,
            camera_name=camera,
            show_window=False,
            salvar_video=False,
            contexto_urbano=contexto_urbano,
            motor_causa_raiz=motor_causa_raiz,
            buffer_seconds=5.0,
            post_seconds=10.0,
        )

        max_f = 1800 if grupo == "real" else None
        detector.run(max_frames=max_f)

        # Obter registros do relatório
        records = detector.relatorio.get_records() if detector.relatorio else []

        # Parsear distribuição de causas caso venha serializada
        for r in records:
            if isinstance(r.get("distribuicao_causas"), str) and r["distribuicao_causas"]:
                try:
                    r["distribuicao_causas"] = json.loads(r["distribuicao_causas"])
                except Exception:
                    pass

        # Estatísticas agrupadas por tipo
        counts = {}
        for r in records:
            t = r.get("tipo", "DESCONHECIDO")
            counts[t] = counts.get(t, 0) + 1

        resultados_globais[vid_id] = {
            "id": vid_id,
            "grupo": grupo,
            "path": path,
            "preset": preset,
            "camera": camera,
            "total_ocorrencias": len(records),
            "contagem_por_tipo": counts,
            "ocorrencias": records,
        }

        print(f"--> Finalizado {vid_id}: Total={len(records)} | Contagem={counts}")

    # Salvar resultado consolidado
    summary_file = _HERE / "outputs" / "resultado_execucao_completa.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(resultados_globais, f, indent=2, ensure_ascii=False)

    print(f"\n============================================================")
    print(f" EXECUÇÃO CONCLUÍDA! Resultado salvo em {summary_file}")
    print(f"============================================================")

if __name__ == "__main__":
    main()
