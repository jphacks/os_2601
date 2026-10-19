const INTERVAL_MS = 1000;
const SAMPLE_LONG_SIDE = 64;
const SAMPLE_SHORT_SIDE = 36;
const MEDIAN_WINDOW = 3;
const MAX_LUMA = 255;

export type MotionScoreHandler = (score: number | null, brightness: number, cameraOk: boolean) => void;

function isCameraLive(video: HTMLVideoElement): boolean {
  const source = video.srcObject;
  return (
    video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA &&
    source instanceof MediaStream &&
    source.getVideoTracks().some((track) => track.readyState === "live" && !track.muted)
  );
}

function toGrayscale(rgba: Uint8ClampedArray): Float32Array {
  const gray = new Float32Array(rgba.length / 4);
  for (let i = 0; i < gray.length; i += 1) {
    gray[i] = 0.299 * rgba[i * 4] + 0.587 * rgba[i * 4 + 1] + 0.114 * rgba[i * 4 + 2];
  }
  return gray;
}

function mean(values: Float32Array): number {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function median(values: ArrayLike<number>): number {
  const sorted = Array.from(values).sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}

export function differenceIgnoringBrightness(current: Float32Array, previous: Float32Array): number {
  const differences = current.map((value, i) => value - previous[i]);
  const shift = median(differences);
  return differences.reduce((sum, difference) => sum + Math.abs(difference - shift), 0) / differences.length;
}

type Frame = { gray: Float32Array; portrait: boolean };

export function startMotionLoop(video: HTMLVideoElement, onScore: MotionScoreHandler): () => void {
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d", { willReadFrequently: true });
  let previous: Frame | null = null;
  let recentDiffs: number[] = [];

  const measure = () => {
    if (!context || !isCameraLive(video)) {
      previous = null;
      recentDiffs = [];
      onScore(null, 0, false);
      return;
    }
    const portrait = video.videoHeight > video.videoWidth;
    canvas.width = portrait ? SAMPLE_SHORT_SIDE : SAMPLE_LONG_SIDE;
    canvas.height = portrait ? SAMPLE_LONG_SIDE : SAMPLE_SHORT_SIDE;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const gray = toGrayscale(context.getImageData(0, 0, canvas.width, canvas.height).data);
    if (previous && previous.portrait === portrait) {
      recentDiffs = [...recentDiffs, differenceIgnoringBrightness(gray, previous.gray) / MAX_LUMA].slice(-MEDIAN_WINDOW);
    }
    previous = { gray, portrait };
    const score = recentDiffs.length === MEDIAN_WINDOW ? median(recentDiffs) : null;
    onScore(score, mean(gray), true);
  };

  const timer = setInterval(measure, INTERVAL_MS);
  return () => clearInterval(timer);
}
