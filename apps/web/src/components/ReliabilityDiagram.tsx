import type { CalibrationBin } from "@/lib/types";

// Diagrama de confiabilidad: probabilidad predicha (x) vs frecuencia observada (y).
// La diagonal es la calibración perfecta. Puntos por encima = subestima; por debajo
// = sobreestima. El tamaño del punto refleja cuántas observaciones cayeron en el bin.
export function ReliabilityDiagram({ bins }: { bins: CalibrationBin[] }) {
  const size = 220;
  const pad = 28;
  const inner = size - pad * 2;
  const x = (p: number) => pad + p * inner;
  const y = (p: number) => pad + (1 - p) * inner;
  const maxCount = Math.max(1, ...bins.map((b) => b.count));

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[260px]" role="img" aria-label="Diagrama de calibración">
      {/* marco */}
      <rect x={pad} y={pad} width={inner} height={inner} className="fill-none stroke-slate-300 dark:stroke-slate-700" />
      {/* diagonal de calibración perfecta */}
      <line x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} className="stroke-slate-400 dark:stroke-slate-600" strokeDasharray="4 3" />
      {/* puntos */}
      {bins.map((b, i) => (
        <circle
          key={i}
          cx={x(b.mean_predicted)}
          cy={y(b.observed_frequency)}
          r={4 + (b.count / maxCount) * 6}
          className="fill-brand-500/70 stroke-brand-600"
        />
      ))}
      {/* etiquetas de ejes */}
      <text x={pad + inner / 2} y={size - 4} textAnchor="middle" className="fill-slate-500 text-[9px]">
        prob. predicha
      </text>
      <text x={8} y={pad + inner / 2} textAnchor="middle" transform={`rotate(-90 8 ${pad + inner / 2})`} className="fill-slate-500 text-[9px]">
        frec. observada
      </text>
    </svg>
  );
}
