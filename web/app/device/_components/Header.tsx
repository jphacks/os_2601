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
    <header className="flex flex-col">
      {info?.mode === "scripted" && (
        <p className="bg-yellow-400 px-4 py-1 text-center text-sm font-bold text-black">scripted</p>
      )}
      <div className="flex flex-col gap-1 px-4 py-3">
        {info && (
          <div className="flex items-center justify-between gap-4 text-lg font-bold">
            <span>
              {info.worksheetId} {info.worksheetTitle}
            </span>
            <span>
              {info.problemNo} / {info.problemCount} 問目
            </span>
          </div>
        )}
        {!connected && <p className="text-base font-bold text-red-600">つながりにくいみたい</p>}
      </div>
    </header>
  );
}
