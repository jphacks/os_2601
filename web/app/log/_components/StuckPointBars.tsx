import type { SessionDetail } from "@/lib/api";

export function StuckPointBars({ points }: { points: SessionDetail["stuck_points"] }) {
  if (points.length === 0) return <p className="text-gray-500">まだ詰まっていません</p>;
  const most = Math.max(...points.map((point) => point.count));
  return (
    <ul className="flex flex-col gap-2">
      {points.map((point) => (
        <li key={point.label} className="grid grid-cols-[minmax(0,14rem)_1fr_3rem] items-center gap-3">
          <span className="truncate">{point.label}</span>
          <span className="h-4 rounded bg-amber-400" style={{ width: `${(point.count / most) * 100}%` }} />
          <span className="text-right tabular-nums">{point.count} 回</span>
        </li>
      ))}
    </ul>
  );
}
