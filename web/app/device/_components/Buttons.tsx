import type { State } from "@/lib/api";

const HINT_STATES: State[] = ["watching", "still", "cooldown"];
const CHECK_STATES: State[] = ["watching", "still", "cooldown", "stuck"];
const NEXT_STATES: State[] = ["watching", "still", "cooldown", "speaking", "stuck"];

type Props = {
  state: State;
  busy: boolean;
  onStart: () => void;
  onHint: () => void;
  onCheck: () => void;
  onNext: () => void;
  onEnd: () => void;
  onRestart: () => void;
};

const PRIMARY =
  "min-h-14 flex-1 rounded-full bg-sky-500 px-6 text-lg font-bold text-white shadow-md transition active:scale-95 disabled:opacity-40 disabled:shadow-none";
const SECONDARY =
  "min-h-11 flex-1 rounded-full bg-white px-4 text-base font-bold text-slate-600 shadow-sm transition active:scale-95 disabled:opacity-40";

export function Buttons({ state, busy, onStart, onHint, onCheck, onNext, onEnd, onRestart }: Props) {
  if (state === "ended") {
    return (
      <button type="button" onClick={onRestart} className={PRIMARY}>
        もう一度はじめる
      </button>
    );
  }
  if (state === "created") {
    return (
      <button type="button" onClick={onStart} disabled={busy} className={PRIMARY}>
        はじめる
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-3">
        <button type="button" onClick={onHint} disabled={busy || !HINT_STATES.includes(state)} className={PRIMARY}>
          ヒント
        </button>
        <button type="button" onClick={onCheck} disabled={busy || !CHECK_STATES.includes(state)} className={PRIMARY}>
          できた
        </button>
      </div>
      <div className="flex gap-3">
        <button type="button" onClick={onNext} disabled={busy || !NEXT_STATES.includes(state)} className={SECONDARY}>
          次へ
        </button>
        <button type="button" onClick={onEnd} disabled={busy} className={SECONDARY}>
          おわる
        </button>
      </div>
    </div>
  );
}
