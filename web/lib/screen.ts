let lock: WakeLockSentinel | null = null;
let wanted = false;

async function acquire(): Promise<void> {
  if (!wanted || lock || typeof navigator === "undefined" || !("wakeLock" in navigator)) return;
  try {
    lock = await navigator.wakeLock.request("screen");
    lock.addEventListener("release", () => {
      lock = null;
    });
  } catch (error) {
    console.warn("[screen] 画面を点けたままにできなかった", error);
  }
}

function onVisible(): void {
  if (document.visibilityState === "visible") void acquire();
}

export function keepScreenOn(): () => void {
  wanted = true;
  void acquire();
  document.addEventListener("visibilitychange", onVisible);
  return () => {
    wanted = false;
    document.removeEventListener("visibilitychange", onVisible);
    void lock?.release();
    lock = null;
  };
}
