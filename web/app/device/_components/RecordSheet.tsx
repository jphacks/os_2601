"use client";

import { useEffect, useRef } from "react";
import type { SessionDetail } from "@/lib/api";
import { SessionRecord } from "@/app/_components/record/SessionRecord";

type Props = {
  session: SessionDetail;
  onClose: () => void;
};

export function RecordSheet({ session, onClose }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const root = document.documentElement;
    const overflow = root.style.overflow;
    root.style.overflow = "hidden";
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      root.style.overflow = overflow;
    };
  }, [onClose]);

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="record-sheet-title" className="fixed inset-0 z-20 flex flex-col overscroll-contain bg-white text-gray-900">
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <h1 id="record-sheet-title" className="text-lg font-bold">今日の記録</h1>
        <button ref={closeRef} type="button" onClick={onClose} className="rounded-full bg-gray-100 px-5 py-2.5 font-bold">
          とじる
        </button>
      </div>
      <div className="flex-1 overflow-y-auto overscroll-contain">
        <div className="mx-auto w-full max-w-3xl p-4">
          <SessionRecord session={session} />
        </div>
      </div>
    </div>
  );
}
