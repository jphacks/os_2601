import type { State } from "@/lib/api";

export function clock(iso: string): string {
  return new Date(iso).toLocaleString("ja-JP", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function sessionStatus(state: State): string {
  return state === "ended" ? "終わり" : "見守り中";
}
