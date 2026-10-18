import type { Mode } from "@/lib/api";

// mode は getSession が成功するまで null。接続の警告は mode が無くても出す
export function Header({ mode, connected }: { mode: Mode | null; connected: boolean }) {
  return (
    <header className="flex w-full flex-col gap-2">
      {mode === "scripted" && (
        <p className="rounded-full bg-yellow-400 px-4 py-1 text-center text-sm font-bold text-black">scripted</p>
      )}
      {!connected && (
        <p role="status" className="rounded-full bg-red-50 px-4 py-1 text-center text-base font-bold text-red-600">
          つながりにくいみたい
        </p>
      )}
    </header>
  );
}
