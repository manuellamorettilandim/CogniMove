import type { CityScenario, Kpi, OperationPoint, SmartCityInvestment } from "@/types";

export const kpis: Kpi[] = [
  { label: "Confianca da IA", value: "94%", trend: "+4,8% nesta semana", tone: "purple" },
  { label: "Infracoes Detectadas", value: "128", trend: "-12% apos intervencoes", tone: "red" },
  { label: "Analises Realizadas", value: "3.482", trend: "24h de operacao", tone: "green" },
  { label: "Status do Sistema", value: "Online", trend: "Todos os sensores ativos", tone: "slate" }
];

export const violationData = [
  { name: "Velocidade", value: 42, fill: "#6D28D9" },
  { name: "Semaforo", value: 24, fill: "#EF4444" },
  { name: "Faixa", value: 18, fill: "#F59E0B" },
  { name: "Conversao", value: 16, fill: "#22C55E" }
];

export const flowData = [
  { hour: "06h", carros: 120, pedestres: 36 },
  { hour: "09h", carros: 240, pedestres: 84 },
  { hour: "12h", carros: 210, pedestres: 70 },
  { hour: "15h", carros: 260, pedestres: 62 },
  { hour: "18h", carros: 390, pedestres: 118 },
  { hour: "21h", carros: 180, pedestres: 54 }
];

export const lineData = [
  { day: "Seg", risco: 58 },
  { day: "Ter", risco: 64 },
  { day: "Qua", risco: 61 },
  { day: "Qui", risco: 72 },
  { day: "Sex", risco: 76 },
  { day: "Sab", risco: 67 },
  { day: "Dom", risco: 48 }
];

export const cityScenarios: CityScenario[] = [
  {
    city: "Sao Paulo",
    trafficIndex: 89,
    risk: 76,
    confidence: 94,
    mainCause: "Excesso de velocidade",
    vehicleFlow: 420
  },
  {
    city: "Curitiba",
    trafficIndex: 62,
    risk: 48,
    confidence: 91,
    mainCause: "Fluxo intenso em cruzamentos",
    vehicleFlow: 260
  },
  {
    city: "Recife",
    trafficIndex: 73,
    risk: 64,
    confidence: 92,
    mainCause: "Baixa visibilidade em horario de pico",
    vehicleFlow: 310
  },
  {
    city: "Belo Horizonte",
    trafficIndex: 68,
    risk: 59,
    confidence: 89,
    mainCause: "Travessias fora da faixa",
    vehicleFlow: 285
  }
];

export const heatmapData = [
  [18, 32, 44, 52, 38],
  [24, 48, 71, 66, 42],
  [36, 58, 86, 79, 51],
  [28, 46, 62, 54, 40],
  [16, 30, 49, 45, 29]
];

export const monitoringStats = [
  { label: "Carros Detectados", value: "247", tone: "purple" },
  { label: "Pedestres", value: "68", tone: "green" },
  { label: "Semaforos", value: "12", tone: "yellow" },
  { label: "Confianca", value: "94%", tone: "slate" }
];

export const futureApiRoutes = {
  dashboard: "/api/dashboard",
  monitoring: "/api/monitoring",
  diagnosis: "/api/diagnosis",
  reports: "/api/reports",
  scenarios: "/api/scenarios",
  operations: "/api/operations"
};

export const operationPoints: OperationPoint[] = [
  {
    id: "central-crossing",
    name: "Cruzamento Central",
    type: "Semaforo urbano",
    risk: "red",
    position: { x: 48, y: 42 },
    image: "https://images.unsplash.com/photo-1517760444937-f6397edcbbcd?auto=format&fit=crop&w=900&q=80",
    vehicles: 824,
    pedestrians: 318,
    peakHour: "18h30",
    violations: 47,
    likelyCause: "Avanco de sinal em fluxo intenso",
    confidence: 96
  },
  {
    id: "main-avenue",
    name: "Avenida Principal",
    type: "Corredor arterial",
    risk: "yellow",
    position: { x: 69, y: 32 },
    image: "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=900&q=80",
    vehicles: 1098,
    pedestrians: 142,
    peakHour: "07h45",
    violations: 28,
    likelyCause: "Excesso de velocidade",
    confidence: 93
  },
  {
    id: "school-zone",
    name: "Escola",
    type: "Zona escolar",
    risk: "yellow",
    position: { x: 29, y: 58 },
    image: "https://images.unsplash.com/photo-1580582932707-520aed937b7b?auto=format&fit=crop&w=900&q=80",
    vehicles: 312,
    pedestrians: 486,
    peakHour: "12h10",
    violations: 19,
    likelyCause: "Travessia fora da faixa",
    confidence: 91
  },
  {
    id: "hospital",
    name: "Hospital",
    type: "Area sensivel",
    risk: "green",
    position: { x: 74, y: 70 },
    image: "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=900&q=80",
    vehicles: 458,
    pedestrians: 267,
    peakHour: "16h20",
    violations: 7,
    likelyCause: "Paradas irregulares",
    confidence: 89
  }
];

export const smartCityInvestments: SmartCityInvestment[] = [
  { id: "radar", label: "Radar Inteligente", cost: 20, impact: 9, description: "Reduz excesso de velocidade nos corredores criticos." },
  { id: "traffic-light", label: "Semaforo Inteligente", cost: 30, impact: 14, description: "Ajusta tempos conforme fluxo e prioridade de pedestres." },
  { id: "raised-crosswalk", label: "Faixa Elevada", cost: 10, impact: 6, description: "Aumenta seguranca em escolas e areas de travessia." },
  { id: "lighting", label: "Melhoria da Iluminacao", cost: 15, impact: 7, description: "Melhora visibilidade em pontos de risco noturno." },
  { id: "education", label: "Educacao no Transito", cost: 8, impact: 4, description: "Reduz comportamento de risco com acoes preventivas." }
];
