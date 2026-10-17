import type { ReactNode, Ref } from "react";

export function VideoFrame({ videoRef, children }: { videoRef: Ref<HTMLVideoElement>; children?: ReactNode }) {
  return (
    <div className="relative aspect-video w-full overflow-hidden bg-black">
      <video ref={videoRef} className="h-full w-full object-cover" muted playsInline autoPlay />
      <div className="absolute bottom-3 left-3">{children}</div>
    </div>
  );
}
