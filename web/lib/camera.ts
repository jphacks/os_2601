const DENIED_ERROR_NAMES = new Set(["NotAllowedError", "SecurityError"]);
const IDEAL_SIZE = { width: { ideal: 1280 }, height: { ideal: 720 } };
const FRAME_LONG_SIDE = 1024;
const JPEG_QUALITY = 0.7;

let stream: MediaStream | null = null;
let currentVideo: HTMLVideoElement | null = null;
let cameraListener: ((live: boolean) => void) | null = null;

async function openStream(video: MediaTrackConstraints): Promise<MediaStream> {
  try {
    return await navigator.mediaDevices.getUserMedia({ video, audio: false });
  } catch (cause) {
    if (cause instanceof DOMException && DENIED_ERROR_NAMES.has(cause.name)) {
      const denied = new Error("カメラの使用が許可されなかった", { cause });
      denied.name = "CameraDenied";
      throw denied;
    }
    throw cause;
  }
}

async function findIphoneCamera(): Promise<MediaDeviceInfo | undefined> {
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices.find((device) => device.kind === "videoinput" && device.label.includes("iPhone"));
}

export async function startCamera(video: HTMLVideoElement): Promise<void> {
  stopCamera();
  stream = await openStream({ facingMode: "environment", ...IDEAL_SIZE });
  if (new URLSearchParams(location.search).get("cam") === "iphone") {
    const iphone = await findIphoneCamera();
    if (iphone) {
      try {
        const iphoneStream = await openStream({ deviceId: { exact: iphone.deviceId }, ...IDEAL_SIZE });
        stopCamera();
        stream = iphoneStream;
      } catch (error) {
        console.warn("[camera] iPhone のカメラが開けないので既定のカメラを使う", error);
      }
    }
  }
  video.muted = true;
  video.playsInline = true;
  video.srcObject = stream;
  try {
    await video.play();
  } catch (error) {
    stopCamera();
    throw error;
  }
  currentVideo = video;
  const opened = stream;
  for (const track of opened.getVideoTracks()) {
    const report = (live: boolean) => {
      if (stream === opened) cameraListener?.(live);
    };
    track.addEventListener("ended", () => report(false));
    track.addEventListener("mute", () => report(false));
    track.addEventListener("unmute", () => report(true));
  }
}

export function watchCamera(listener: (live: boolean) => void): () => void {
  cameraListener = listener;
  return () => {
    if (cameraListener === listener) cameraListener = null;
  };
}

export function isCameraLive(video: HTMLVideoElement): boolean {
  const source = video.srcObject;
  return (
    video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA &&
    source instanceof MediaStream &&
    source.getVideoTracks().some((track) => track.readyState === "live" && !track.muted)
  );
}

export function captureFrame(): Promise<Blob> {
  const video = currentVideo;
  if (!video || !isCameraLive(video)) {
    return Promise.reject(new Error("カメラの映像が無いか、止まっている"));
  }
  const scale = Math.min(1, FRAME_LONG_SIDE / Math.max(video.videoWidth, video.videoHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(video.videoWidth * scale);
  canvas.height = Math.round(video.videoHeight * scale);
  const context = canvas.getContext("2d");
  if (!context) return Promise.reject(new Error("canvas の 2D コンテキストが取れない"));
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
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
  currentVideo = null;
}
