const DENIED_ERROR_NAMES = new Set(["NotAllowedError", "SecurityError"]);
const JPEG_QUALITY = 0.7;

let stream: MediaStream | null = null;

export async function startCamera(video: HTMLVideoElement): Promise<void> {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
  } catch (cause) {
    if (cause instanceof DOMException && DENIED_ERROR_NAMES.has(cause.name)) {
      const denied = new Error("カメラの使用が許可されなかった", { cause });
      denied.name = "CameraDenied";
      throw denied;
    }
    throw cause;
  }
  video.muted = true;
  video.playsInline = true;
  video.srcObject = stream;
  await video.play();
}

export function captureFrame(): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = 1;
  canvas.height = 1;
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("フレームを JPEG にできなかった"))),
      "image/jpeg",
      JPEG_QUALITY,
    );
  });
}

export function stopCamera(): void {
  stream?.getTracks().forEach((track) => track.stop());
  stream = null;
}
