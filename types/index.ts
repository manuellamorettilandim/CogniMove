import type { LucideIcon } from "lucide-react";

export type PageKey =
  | "dashboard"
  | "monitoring"
  | "diagnosis"
  | "reports"
  | "scenarios"
  | "operations"
  | "interactive"
  | "about"
  | "settings";

export type NavItem = {
  key: PageKey;
  label: string;
  icon: LucideIcon;
};

export type Kpi = {
  label: string;
  value: string;
  trend: string;
  tone: "purple" | "green" | "red" | "yellow" | "slate";
};

export type CityScenario = {
  city: string;
  trafficIndex: number;
  risk: number;
  confidence: number;
  mainCause: string;
  vehicleFlow: number;
};

export type DiagnosisResult = {
  risk: string;
  cause: string;
  confidence: string;
  recommendations: string[];
};

export type OperationPoint = {
  id: string;
  name: string;
  type: string;
  risk: "green" | "yellow" | "red";
  position: {
    x: number;
    y: number;
  };
  image: string;
  vehicles: number;
  pedestrians: number;
  peakHour: string;
  violations: number;
  likelyCause: string;
  confidence: number;
};

export type SmartCityInvestment = {
  id: string;
  label: string;
  cost: number;
  impact: number;
  description: string;
};
