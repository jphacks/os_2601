type Props = {
  worksheetId: string;
  worksheetTitle: string;
  problemNo: number;
  problemCount: number;
};

export function Header({ worksheetId, worksheetTitle, problemNo, problemCount }: Props) {
  return (
    <header className="flex items-center justify-between gap-4 px-4 py-3 text-lg font-bold">
      <span>
        {worksheetId} {worksheetTitle}
      </span>
      <span>
        {problemNo} / {problemCount} 問目
      </span>
    </header>
  );
}
