import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { heatmapData } from "@/mock/traffic-data";

export function HeatmapCard() {
  return (
    <Card>
      <CardTitle>Heatmap de risco</CardTitle>
      <CardDescription>Pontos criticos por regiao e horario</CardDescription>
      <div className="mt-5 grid grid-cols-5 gap-2">
        {heatmapData.flatMap((row, rowIndex) =>
          row.map((value, columnIndex) => (
            <div
              key={`${rowIndex}-${columnIndex}`}
              className="flex aspect-square items-center justify-center rounded-xl text-xs font-semibold text-white"
              style={{ backgroundColor: `rgba(109, 40, 217, ${Math.max(value / 100, 0.18)})` }}
            >
              {value}
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
