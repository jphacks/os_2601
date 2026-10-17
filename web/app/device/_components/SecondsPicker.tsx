// docs/06 の「状態と表示」の created の選択肢
const CHOICES = [
  { seconds: 10, label: "10 秒" },
  { seconds: 20, label: "20 秒" },
  { seconds: 30, label: "30 秒" },
  { seconds: 60, label: "1 分" },
  { seconds: 180, label: "3 分" },
  { seconds: 300, label: "5 分" },
  { seconds: 600, label: "10 分" },
  { seconds: 1200, label: "20 分" },
];

export function nearestChoice(seconds: number): number {
  return CHOICES.reduce((best, choice) =>
    Math.abs(choice.seconds - seconds) < Math.abs(best.seconds - seconds) ? choice : best,
  ).seconds;
}

type Props = {
  value: number;
  onChange: (seconds: number) => void;
};

export function SecondsPicker({ value, onChange }: Props) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-2 text-base font-bold text-slate-700">止まったと判定する秒数</legend>
      <div className="flex flex-wrap gap-2">
        {CHOICES.map(({ seconds, label }) => (
          <button
            key={seconds}
            type="button"
            onClick={() => onChange(seconds)}
            aria-pressed={value === seconds}
            className={`min-h-11 rounded-full px-4 text-base font-bold shadow-sm transition active:scale-95 ${
              value === seconds ? "bg-sky-500 text-white" : "bg-white text-slate-600"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
