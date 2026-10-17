import type { Mode } from "@/lib/api";

type Props = {
  worksheetId: string;
  worksheetTitle: string;
  problemNo: number;
  problemCount: number;
  mode: Mode;
  connected: boolean;
};

export function Header({ worksheetId, worksheetTitle, problemNo, problemCount, mode, connected }: Props) {
  return (
    <header className="flex flex-col">
      {mode === "scripted" && (
        <p className="bg-yellow-400 px-4 py-1 text-center text-sm font-bold text-black">scripted</p>
      )}
      <div className="flex flex-col gap-1 px-4 py-3">
        <div className="flex items-center justify-between gap-4 text-lg font-bold">
          <span>
            {worksheetId} {worksheetTitle}
          </span>
          <span>
            {problemNo} / {problemCount} 問目
          </span>
        </div>
        {!connected && <p className="text-base font-bold text-red-600">つながりにくいみたい</p>}
      </div>
    </header>
  );
}
