import type { Mode } from "@/lib/api";

type Info = {
  worksheetId: string;
  worksheetTitle: string;
  problemNo: number;
  problemCount: number;
  mode: Mode;
};

// info は getSession が成功するまで null。接続の警告は info が無くても出す
export function Header({ info, connected }: { info: Info | null; connected: boolean }) {
  return (
    <header className="flex w-full flex-col gap-2">
      {info?.mode === "scripted" && (
        <p className="rounded-full bg-yellow-400 px-4 py-1 text-center text-sm font-bold text-black">scripted</p>
      )}
      {info && (
        <div className="flex w-full items-center justify-between gap-4 rounded-full bg-white px-5 py-2 text-base font-bold text-slate-800 shadow-sm">
          <span>
            {info.worksheetId} {info.worksheetTitle}
          </span>
          <span className="rounded-full bg-sky-100 px-3 py-0.5 text-sky-800">
            {info.problemNo} / {info.problemCount} 問目
          </span>
        </div>
      )}
      {!connected && (
        <p className="rounded-full bg-red-50 px-4 py-1 text-center text-base font-bold text-red-600">
          つながりにくいみたい
        </p>
      )}
    </header>
  );
}
