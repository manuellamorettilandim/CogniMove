"""
CogniMove — Mapeamento de Recomendações Urbanas por Causa-Raiz (Módulo 4)
"""
from __future__ import annotations

from backend.analytics.causa_raiz import Causa

RECOMENDACOES_POR_CAUSA: dict[str, str] = {
    Causa.PINTURA_DESGASTADA_AUSENTE.value: "Recomenda-se repintura imediata e aplicação de sinalização retrorrefletiva na faixa de pedestres para garantir visibilidade noturna e em dias chuvosos.",
    Causa.TEMPO_SEMAFORICO_INADEQUADO.value: "Recomenda-se reprogramação dos ciclos semafóricos junto à CET, com aumento do tempo de verde e tempo de amarelo de segurança nos horários de pico.",
    Causa.CONGESTIONAMENTO.value: "Recomenda-se sincronismo de onda verde e escalonamento de agentes de trânsito para evitar retenção na área de bloqueio de cruzamento.",
    Causa.AUSENCIA_DE_SEGREGADOR_FISICO.value: "Recomenda-se instalação de tachões ou defensas físicas segregando a faixa exclusiva/ciclovia para coibir invasões recorrentes.",
    Causa.SINALIZACAO_POUCO_VISIVEL.value: "Recomenda-se poda de árvores que obstruem placas e repaginação da geometria de aproximação viária.",
    Causa.CONDUTA_DO_CONDUTOR.value: "Recomenda-se intensificação da fiscalização eletrônica/presencial e campanhas educativas de conscientização no trecho.",
}
