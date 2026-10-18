let lock: WakeLockSentinel | null = null;
let generation = 0;

async function acquire(owner: number): Promise<void> {
  if (owner !== generation || lock || typeof navigator === "undefined" || !("wakeLock" in navigator)) return;
  try {
    const sentinel = await navigator.wakeLock.request("screen");
    if (owner !== generation || lock) {
      void sentinel.release();
      return;
    }
    lock = sentinel;
    sentinel.addEventListener("release", () => {
      if (lock === sentinel) lock = null;
    });
  } catch (error) {
    console.warn("[screen] 画面を点けたままにできなかった", error);
  }
}

export function keepScreenOn(): () => void {
  const owner = ++generation;
  const onVisible = () => {
    if (document.visibilityState === "visible") void acquire(owner);
  };
  void acquire(owner);
  document.addEventListener("visibilitychange", onVisible);
  return () => {
    document.removeEventListener("visibilitychange", onVisible);
    if (owner !== generation) return;
    generation += 1;
    void lock?.release();
    lock = null;
  };
}
