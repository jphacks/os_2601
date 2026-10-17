import type { State } from "@/lib/api";

const GRAY = "bg-gray-500 text-white";
const GREEN = "bg-green-600 text-white";
const YELLOW = "bg-yellow-400 text-black";
const BLUE = "bg-blue-600 text-white";

// docs/06 の「状態と表示」。still は watching と同じ見た目にする
const BADGES: Record<State, { label: string; color: string }> = {
  created: { label: "はじめる前", color: GRAY },
  watching: { label: "見守り中", color: GREEN },
  still: { label: "見守り中", color: GREEN },
  stuck: { label: "考え中？", color: YELLOW },
  speaking: { label: "となり", color: BLUE },
  cooldown: { label: "見守り中", color: GREEN },
  checking: { label: "見てるよ", color: BLUE },
  ended: { label: "おつかれさま", color: GREEN },
};

export function StateBadge({ state }: { state: State }) {
  const { label, color } = BADGES[state];
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-base font-bold ${color}`}>
      <span aria-hidden>●</span>
      {label}
    </span>
  );
}
