const LANG = "ja-JP";
const RESTART_DELAY_MS = 500;
const RETRY_DELAY_MS = 3000;
const FATAL_ERRORS = new Set(["not-allowed", "service-not-allowed", "audio-capture", "language-not-supported"]);
const QUIET_ERRORS = new Set(["no-speech", "aborted"]);

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
let nextBeginDelayMs = RESTART_DELAY_MS;
let status = "未開始";
let restartTimer: ReturnType<typeof setTimeout> | undefined;

function createRecognizer(): Recognizer | null {
  const speechWindow = window as unknown as {
    SpeechRecognition?: RecognizerClass;
    webkitSpeechRecognition?: RecognizerClass;
  };
  const Recognizer = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
  if (!Recognizer) {
    status = "このブラウザは非対応";
    return null;
  }
  const created = new Recognizer();
  created.lang = LANG;
  created.continuous = false;
  created.interimResults = false;
  created.onresult = (event) => {
    if (!wanted) return;
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const text = event.results[i][0].transcript.trim();
      if (!event.results[i].isFinal || !text) continue;
      status = `聞こえた：${text}`;
      onHeard(text);
    }
  };
  created.onerror = (event) => {
    if (FATAL_ERRORS.has(event.error)) {
      console.warn("[voice] 聞き取りをやめる", event.error);
      status = `やめた：${event.error}`;
      blocked = true;
      wanted = false;
    } else if (!QUIET_ERRORS.has(event.error)) {
      console.warn("[voice] 聞き取りのエラー。少し待って再開", event.error);
      status = `エラー：${event.error}`;
      nextBeginDelayMs = RETRY_DELAY_MS;
    }
  };
  created.onend = () => {
    running = false;
    if (wanted) scheduleBegin(nextBeginDelayMs);
    nextBeginDelayMs = RESTART_DELAY_MS;
  };
  return created;
}

function scheduleBegin(delayMs: number): void {
  clearTimeout(restartTimer);
  restartTimer = setTimeout(begin, delayMs);
}

function begin(): void {
  if (!wanted || running || blocked || !recognizer) return;
  try {
    recognizer.start();
    running = true;
    status = "聞いている";
  } catch (error) {
    console.warn("[voice] 聞き取りを始められない。少し待って再開", error);
    status = `始められない：${error instanceof Error ? error.name : String(error)}`;
    scheduleBegin(RETRY_DELAY_MS);
  }
}

export function startListening(handler: (text: string) => void): () => void {
  onHeard = handler;
  if (typeof window === "undefined" || blocked) return stopListening;
  if (new URLSearchParams(window.location.search).get("voice") === "0") {
    status = "オフ（voice=0）";
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
  return status;
}

export function stopListening(): void {
  wanted = false;
  clearTimeout(restartTimer);
  if (running) recognizer?.abort();
}
