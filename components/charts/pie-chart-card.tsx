"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { violationData } from "@/mock/traffic-data";

export function PieChartCard() {
  return (
    <Card className="h-72">
      <CardTitle>Infracoes por tipo</CardTitle>
      <CardDescription>Distribuicao das ocorrencias analisadas</CardDescription>
      <div className="mt-4 h-52">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={violationData} dataKey="value" nameKey="name" innerRadius={48} outerRadius={78} paddingAngle={4}>
              {violationData.map((entry) => (
                <Cell key={entry.name} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
