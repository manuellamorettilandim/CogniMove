"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { flowData } from "@/mock/traffic-data";

export function BarChartCard({ data = flowData }: { data?: typeof flowData }) {
  return (
    <Card className="h-72">
      <CardTitle>Fluxo monitorado</CardTitle>
      <CardDescription>Veiculos e pedestres por horario</CardDescription>
      <div className="mt-4 h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
            <XAxis dataKey="hour" axisLine={false} tickLine={false} fontSize={12} />
            <YAxis axisLine={false} tickLine={false} fontSize={12} />
            <Tooltip cursor={{ fill: "#F8FAFC" }} />
            <Bar dataKey="carros" radius={[8, 8, 0, 0]} fill="#6D28D9" />
            <Bar dataKey="pedestres" radius={[8, 8, 0, 0]} fill="#22C55E" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
