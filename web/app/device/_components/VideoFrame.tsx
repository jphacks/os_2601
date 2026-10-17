import type { ReactNode, Ref } from "react";

type Props = {
  videoRef: Ref<HTMLVideoElement>;
  dark: boolean;
  debugText: string | null;
  children?: ReactNode;
};

export function VideoFrame({ videoRef, dark, debugText, children }: Props) {
  return (
    <div className="relative aspect-video w-full overflow-hidden bg-black">
      <video ref={videoRef} className="h-full w-full object-cover" muted playsInline autoPlay />
      {dark && (
        <p className="absolute inset-x-0 top-1/2 -translate-y-1/2 bg-black/60 py-2 text-center text-lg font-bold text-white">
          明るさが足りません
        </p>
      )}
      {debugText && (
        <p className="absolute top-2 right-2 rounded bg-black/60 px-2 py-1 font-mono text-xs text-white">{debugText}</p>
      )}
      <div className="absolute bottom-3 left-3">{children}</div>
    </div>
  );
}
