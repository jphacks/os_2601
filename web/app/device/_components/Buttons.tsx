"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import type { State } from "@/lib/api";

const HINT_STATES: State[] = ["watching", "still", "cooldown"];
const CHECK_STATES: State[] = ["watching", "still", "cooldown", "stuck"];
const NEXT_STATES: State[] = ["watching", "still", "cooldown", "speaking", "stuck"];
const END_CONFIRM_MS = 4000;

type Props = {
  state: State;
  cameraStopped: boolean;
  busy: boolean;
  onStart: () => void;
  onHint: () => void;
  onCheck: () => void;
  onNext: () => void;
  onEnd: () => void;
  onRestart: () => void;
};

const PRIMARY =
  "min-h-14 flex-1 rounded-full bg-sky-700 px-6 text-lg font-bold text-white shadow-md transition active:scale-95 disabled:opacity-40 disabled:shadow-none";
const SECONDARY =
  "min-h-11 flex-1 rounded-full bg-white px-4 text-base font-bold text-slate-600 shadow-sm transition active:scale-95 disabled:opacity-40";
const CONFIRMING =
  "min-h-11 flex-1 rounded-full bg-rose-700 px-4 text-base font-bold text-white shadow-sm transition active:scale-95 disabled:opacity-40";

export function Buttons({ state, cameraStopped, busy, onStart, onHint, onCheck, onNext, onEnd, onRestart }: Props) {
  const [confirmingEnd, setConfirmingEnd] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const lastFocusedRef = useRef<Element | null>(null);
  const showsStart = state === "created" || cameraStopped;

  useEffect(() => {
    if (!confirmingEnd) return;
    const timer = setTimeout(() => setConfirmingEnd(false), END_CONFIRM_MS);
    return () => clearTimeout(timer);
  }, [confirmingEnd]);

  useEffect(() => {
    const lastFocused = lastFocusedRef.current;
    const lost = lastFocused !== null && !lastFocused.isConnected && document.activeElement === document.body;
    if (!lost || state === "ended") return;
    const root = rootRef.current;
    (root?.querySelector<HTMLButtonElement>("button:not(:disabled)") ?? root)?.focus();
  }, [showsStart, state]);

  const startButton = (
    <button type="button" onClick={onStart} disabled={busy} className={PRIMARY}>
      はじめる
    </button>
  );
  const endButton = (
    <button
      type="button"
      onClick={() => {
        if (!confirmingEnd) {
          setConfirmingEnd(true);
          return;
        }
        setConfirmingEnd(false);
        onEnd();
      }}
      disabled={busy}
      className={confirmingEnd ? CONFIRMING : SECONDARY}
    >
      {confirmingEnd ? "本当におわる？" : "おわる"}
    </button>
  );
  let content: ReactNode;
  if (state === "ended") {
    content = (
      <button type="button" onClick={onRestart} className={PRIMARY}>
        もう一度はじめる
      </button>
    );
  } else if (state === "created") {
    content = startButton;
  } else {
    content = (
      <>
        <div className="flex gap-3">
          {cameraStopped && startButton}
          {!cameraStopped && (
            <>
              <button type="button" onClick={onHint} disabled={busy || !HINT_STATES.includes(state)} className={PRIMARY}>
                ヒント
              </button>
              <button type="button" onClick={onCheck} disabled={busy || !CHECK_STATES.includes(state)} className={PRIMARY}>
                できた
              </button>
            </>
          )}
        </div>
        <div className="flex gap-3">
          {!cameraStopped && (
            <button type="button" onClick={onNext} disabled={busy || !NEXT_STATES.includes(state)} className={SECONDARY}>
              次へ
            </button>
          )}
          {endButton}
        </div>
      </>
    );
  }

  return (
    <div
      ref={rootRef}
      tabIndex={-1}
      onFocus={(event) => {
        lastFocusedRef.current = event.target;
      }}
      className="flex flex-col gap-3 outline-none"
    >
      {content}
    </div>
  );
}
