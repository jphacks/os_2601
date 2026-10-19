import type { State } from "./api";

export function dateTime(iso: string): string {
  return new Date(iso).toLocaleString("ja-JP", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function duration(seconds: number): string {
  return seconds < 60 ? `${seconds} 秒` : `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`;
}

export function sessionStatus(state: State): string {
  if (state === "created") return "はじめる前";
  return state === "ended" ? "終わり" : "見守り中";
}
