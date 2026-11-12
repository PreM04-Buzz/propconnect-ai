import { useMemo, useRef, useState } from "react";
import type { MarketSeries } from "../api/client";

export const SERIES_COLORS = ["#1c2b3a", "#c48a2c", "#2d7d7a"];
const W = 800, H = 320, L = 64, R = 16, T = 16, B = 34;

function niceStep(max: number) {
  const raw = max / 4;
  const mag = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
}
const short = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}k` : `${Math.round(n)}`);
const monthLabel = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString("en-US", { month: "short", year: "numeric" });

/** A line chart drawn as plain SVG. "index" mode shows each area as a % of its own 2019 average. */
export function MarketChart({ series, mode }: { series: MarketSeries[]; mode: "count" | "index" }) {
  const ref = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<number | null>(null);

  const data = useMemo(() => {
    const months = series[0]?.points.map((p) => p.month) ?? [];
    const lines = series.map((s) => {
      const base2019 = s.points.filter((p) => p.month.startsWith("2019"));
      const avg = base2019.length ? base2019.reduce((a, p) => a + p.inventory, 0) / base2019.length : null;
      const byMonth = new Map(s.points.map((p) => [p.month, mode === "index" && avg ? (p.inventory / avg) * 100 : p.inventory]));
      return months.map((m) => byMonth.get(m) ?? null);
    });
    const max = Math.max(1, ...lines.flat().filter((v): v is number => v !== null));
    const step = niceStep(max);
    const top = Math.ceil(max / step) * step;
    return { months, lines, top, step };
  }, [series, mode]);

  const { months, lines, top, step } = data;
  const x = (i: number) => L + (i / Math.max(1, months.length - 1)) * (W - L - R);
  const y = (v: number) => T + (1 - v / top) * (H - T - B);
  const fmt = (v: number) => (mode === "index" ? `${Math.round(v)}%` : Math.round(v).toLocaleString());

  function onMove(e: React.PointerEvent<SVGSVGElement>) {
    const box = ref.current?.getBoundingClientRect();
    if (!box || !months.length) return;
    const px = ((e.clientX - box.left) / box.width) * W;
    setHover(Math.min(months.length - 1, Math.max(0, Math.round(((px - L) / (W - L - R)) * (months.length - 1)))));
  }

  const yTicks = Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step);
  const janIdx = months.map((m, i) => (m.slice(5, 7) === "01" ? i : -1)).filter((i) => i >= 0);
  const label = series.map((s) => `${s.region_name}: ${s.stats.summary}`).join(" ");

  return (
    <div className="mchart">
      <svg ref={ref} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}
           onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className="mchart-grid" />
            <text x={L - 8} y={y(v) + 4} textAnchor="end" className="mchart-axis">{mode === "index" ? `${v}%` : short(v)}</text>
          </g>
        ))}
        {mode === "index" && <line x1={L} x2={W - R} y1={y(100)} y2={y(100)} className="mchart-base" />}
        {janIdx.map((i) => (
          <text key={i} x={x(i)} y={H - 10} textAnchor="middle" className="mchart-axis">{months[i]?.slice(0, 4)}</text>
        ))}
        {lines.map((line, si) => {
          const d = line.map((v, i) => (v === null ? "" : `${i === 0 || line[i - 1] === null ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`)).join(" ");
          return <path key={si} d={d} fill="none" stroke={SERIES_COLORS[si]} strokeWidth={2.4} strokeLinejoin="round" />;
        })}
        {hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} className="mchart-cursor" />
            {lines.map((line, si) => line[hover] !== null && (
              <circle key={si} cx={x(hover)} cy={y(line[hover] as number)} r={4.5} fill={SERIES_COLORS[si]} stroke="#fff" strokeWidth={1.5} />
            ))}
          </g>
        )}
      </svg>
      {hover !== null && months[hover] && (
        <div className="mchart-tip" style={{ left: `${Math.min(85, Math.max(15, (x(hover) / W) * 100))}%` }} role="status">
          <b>{monthLabel(months[hover] as string)}</b>
          {series.map((s, si) => {
            const v = lines[si]?.[hover];
            return v === null || v === undefined ? null : (
              <span key={s.region_id}><i style={{ background: SERIES_COLORS[si] }} />{s.region_name}: {fmt(v)}</span>
            );
          })}
        </div>
      )}
    </div>
  );
}
