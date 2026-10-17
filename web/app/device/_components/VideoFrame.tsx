import type { Ref } from "react";

type Props = {
  videoRef: Ref<HTMLVideoElement>;
  dark: boolean;
  debugText: string | null;
};

// 映像は右上に小さく出す。動きの計算は video 要素の表示の大きさに関係しない
export function VideoFrame({ videoRef, dark, debugText }: Props) {
  return (
    <div className="flex w-28 shrink-0 flex-col gap-1">
      <div className="relative aspect-video w-full overflow-hidden rounded-2xl bg-slate-900 shadow-md ring-2 ring-white">
        <video ref={videoRef} className="h-full w-full object-cover" muted playsInline autoPlay />
      </div>
      {dark && (
        <p className="rounded-full bg-slate-900/70 px-2 py-0.5 text-center text-[10px] font-bold text-white">
          明るさが足りません
        </p>
      )}
      {debugText && (
        <p className="rounded-lg bg-slate-900/70 px-2 py-0.5 font-mono text-[10px] text-white">{debugText}</p>
      )}
    </div>
  );
}
