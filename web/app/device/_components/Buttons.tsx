import type { State } from "@/lib/api";

// docs/06 の「ボタンの動き」。speaking と stuck の間は主ボタンを押せない
const PRIMARY_STATES: State[] = ["watching", "still", "cooldown"];
const NEXT_STATES: State[] = ["watching", "still", "cooldown", "speaking"];

type Props = {
  state: State;
  busy: boolean;
  onStart: () => void;
  onHint: () => void;
  onCheck: () => void;
  onNext: () => void;
  onEnd: () => void;
};

const PRIMARY =
  "min-h-14 flex-1 rounded-full bg-sky-500 px-6 text-lg font-bold text-white shadow-md transition active:scale-95 disabled:opacity-40 disabled:shadow-none";
const SECONDARY =
  "min-h-11 flex-1 rounded-full bg-white px-4 text-base font-bold text-slate-600 shadow-sm transition active:scale-95 disabled:opacity-40";

export function Buttons({ state, busy, onStart, onHint, onCheck, onNext, onEnd }: Props) {
  if (state === "created") {
    return (
      <button type="button" onClick={onStart} disabled={busy} className={PRIMARY}>
        はじめる
      </button>
    );
  }

  const primaryEnabled = !busy && PRIMARY_STATES.includes(state);
  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-3">
        <button type="button" onClick={onHint} disabled={!primaryEnabled} className={PRIMARY}>
          ヒント
        </button>
        <button type="button" onClick={onCheck} disabled={!primaryEnabled} className={PRIMARY}>
          できた
        </button>
      </div>
      <div className="flex gap-3">
        <button type="button" onClick={onNext} disabled={busy || !NEXT_STATES.includes(state)} className={SECONDARY}>
          次へ
        </button>
        <button type="button" onClick={onEnd} disabled={busy || state === "ended"} className={SECONDARY}>
          おわる
        </button>
      </div>
    </div>
  );
}
