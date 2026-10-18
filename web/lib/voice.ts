const LANG = "ja-JP";
const RESTART_DELAY_MS = 500;
const QUICK_END_MS = 500;
const QUICK_END_RETRY_DELAY_MS = 1000;
const RETRY_DELAY_MS = 3000;
const MIC_BUSY_RETRY_DELAY_MS = 30000;
const NEEDS_GESTURE_ERROR = "not-allowed";
const MIC_BUSY_ERROR = "audio-capture";
const FATAL_ERRORS = new Set(["service-not-allowed", "language-not-supported"]);
const QUIET_ERRORS = new Set(["no-speech", "aborted"]);
const EVENTS_SHOWN = 4;

type RecognitionResultEvent = { resultIndex: number; results: SpeechRecognitionResultList };

type Recognizer = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: RecognitionResultEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  abort: () => void;
};

type RecognizerClass = new () => Recognizer;

let recognizer: Recognizer | null = null;
let onHeard: (text: string) => void = () => {};
let wanted = false;
let running = false;
let blocked = false;
let waitingForTap = false;
let startedAt = 0;
let heardSinceStart = false;
let notBefore = 0;
let nextBeginDelayMs = RESTART_DELAY_MS;
let restartTimer: ReturnType<typeof setTimeout> | undefined;
const events: string[] = ["未開始"];

function note(event: string): void {
  events.push(event);
  events.splice(0, events.length - EVENTS_SHOWN);
}

function createRecognizer(): Recognizer | null {
  const speechWindow = window as unknown as {
    SpeechRecognition?: RecognizerClass;
    webkitSpeechRecognition?: RecognizerClass;
  };
  const Recognizer = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
  if (!Recognizer) {
    note("このブラウザは非対応");
    return null;
  }
  const created = new Recognizer();
  created.lang = LANG;
  created.continuous = false;
  created.interimResults = true;
  created.onresult = (event) => {
    if (!wanted) return;
    heardSinceStart = true;
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const text = event.results[i][0].transcript.trim();
      if (!text) continue;
      if (!event.results[i].isFinal) {
        note(`途中 ${text.length} 字`);
        continue;
      }
      note(`聞こえた ${text.length} 字`);
      onHeard(text);
    }
  };
  created.onerror = (event) => {
    note(`error:${event.error}`);
    if (event.error === NEEDS_GESTURE_ERROR) {
      console.warn("[voice] 操作の直後でないと始められない。次のタップで始め直す");
      waitingForTap = true;
    } else if (FATAL_ERRORS.has(event.error)) {
      console.warn("[voice] 聞き取りをやめる", event.error);
      blocked = true;
      wanted = false;
    } else if (event.error === MIC_BUSY_ERROR) {
      console.warn(`[voice] マイクを取れない（通話中など）。${MIC_BUSY_RETRY_DELAY_MS / 1000} 秒待って再開`);
      running = false;
      nextBeginDelayMs = MIC_BUSY_RETRY_DELAY_MS;
      scheduleBegin(MIC_BUSY_RETRY_DELAY_MS);
    } else if (!QUIET_ERRORS.has(event.error)) {
      console.warn("[voice] 聞き取りのエラー。少し待って再開", event.error);
      nextBeginDelayMs = RETRY_DELAY_MS;
    }
  };
  created.onend = () => {
    running = false;
    note("end");
    const endedQuickly = !heardSinceStart && Date.now() - startedAt < QUICK_END_MS;
    const delayMs = endedQuickly ? Math.max(nextBeginDelayMs, QUICK_END_RETRY_DELAY_MS) : nextBeginDelayMs;
    if (wanted && !waitingForTap) scheduleBegin(delayMs);
    nextBeginDelayMs = RESTART_DELAY_MS;
  };
  window.addEventListener("pointerdown", () => {
    if (!waitingForTap) return;
    waitingForTap = false;
    note("タップ");
    begin();
  });
  return created;
}

function scheduleBegin(delayMs: number): void {
  clearTimeout(restartTimer);
  notBefore = Date.now() + delayMs;
  restartTimer = setTimeout(begin, delayMs);
}

function begin(): void {
  if (!wanted || running || blocked || waitingForTap || !recognizer) return;
  if (Date.now() < notBefore) return;
  try {
    recognizer.start();
    running = true;
    startedAt = Date.now();
    heardSinceStart = false;
    note("start");
  } catch (error) {
    console.warn("[voice] 聞き取りを始められない。少し待って再開", error);
    note(`start失敗:${error instanceof Error ? error.name : String(error)}`);
    scheduleBegin(RETRY_DELAY_MS);
  }
}

export function startListening(handler: (text: string) => void): () => void {
  onHeard = handler;
  if (typeof window === "undefined" || blocked) return stopListening;
  if (new URLSearchParams(window.location.search).get("voice") === "0") {
    note("オフ（voice=0）");
    return stopListening;
  }
  recognizer ??= createRecognizer();
  wanted = true;
  begin();
  return stopListening;
}

export function primeListening(): void {
  startListening(() => {});
}

export function voiceStatus(): string {
  return events.join(" → ");
}

export function stopListening(): void {
  wanted = false;
  clearTimeout(restartTimer);
  if (running) recognizer?.abort();
}
