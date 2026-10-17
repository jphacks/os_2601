const INTERVAL_MS = 1000;
const STUB_SCORE = 0.2;
const STUB_BRIGHTNESS = 120;

export type MotionScoreHandler = (score: number | null, brightness: number, cameraOk: boolean) => void;

export function startMotionLoop(video: HTMLVideoElement, onScore: MotionScoreHandler): () => void {
  const timer = setInterval(() => onScore(STUB_SCORE, STUB_BRIGHTNESS, true), INTERVAL_MS);
  return () => clearInterval(timer);
}
