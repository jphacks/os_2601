type Props = {
  worksheetId: string;
  worksheetTitle: string;
  problemNo: number;
  problemCount: number;
  connected: boolean;
};

export function Header({ worksheetId, worksheetTitle, problemNo, problemCount, connected }: Props) {
  return (
    <header className="flex flex-col gap-1 px-4 py-3">
      <div className="flex items-center justify-between gap-4 text-lg font-bold">
        <span>
          {worksheetId} {worksheetTitle}
        </span>
        <span>
          {problemNo} / {problemCount} 問目
        </span>
      </div>
      {!connected && <p className="text-base font-bold text-red-600">つながりにくいみたい</p>}
    </header>
  );
}
